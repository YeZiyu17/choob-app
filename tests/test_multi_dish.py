"""Checks for regional agreement and the original recognition response."""
import unittest

from PIL import Image

from multi_dish import _WINDOWS, _grid_windows, recognize_meal
from recognition import DishRecognizer


def score(label, margin, relative_score=0.93):
    return {
        "support_margin": margin,
        "support_similarity": 0.31,
        "top_3": [
            {"dish_name": label, "relative_score": relative_score},
            {"dish_name": "pasta", "relative_score": 0.03},
            {"dish_name": "ramen", "relative_score": 0.02},
        ],
    }


def provisional_score(label, margin=0.05, legacy_label="pasta"):
    return {
        **score(legacy_label, -0.03, 0.45),
        "calibrated_accepted": False,
        "suggestion_useful": True,
        "suggestion_filter_reasons": [],
        "suggestion_top_3": [{"dish_name": label, "similarity": 0.3}],
        "suggestion_similarity": 0.3,
        "food_over_non_food_margin": margin,
        "review_label": label,
        "review_mode": "provisional",
    }


class MultiDishPolicyTests(unittest.TestCase):
    def setUp(self):
        self.recognizer = DishRecognizer.__new__(DishRecognizer)
        self.recognizer.threshold = 0.005
        self.recognizer.labels = ["pizza", "sushi", "pasta", "ramen", "hamburger"]
        self.recognizer.encode_images = lambda images: images
        self.image = Image.new("RGB", (400, 300))

    def run_recognition(self, whole, regional):
        scores = [whole, *(regional.get(window, score("pasta", -0.02)) for window in _WINDOWS)]
        self.recognizer.score_features = lambda images: scores[:len(images)]
        return recognize_meal(self.recognizer, self.image)

    def test_distinct_regions_can_support_multiple_dishes_when_whole_image_abstains(self):
        result = self.run_recognition(score("pasta", -0.02), {
            (0, 0, 0.55, 1): score("pizza", 0.05),
            (0, 0, 0.55, 0.55): score("pizza", 0.04),
            (0.45, 0, 1, 1): score("sushi", 0.04),
            (0.45, 0, 1, 0.55): score("sushi", 0.03),
        })
        self.assertTrue(result["accepted"])
        self.assertEqual(result["recognition_mode"], "multi")
        self.assertEqual({dish["dish_name"] for dish in result["dishes"]}, {"Pizza", "Sushi"})

    def test_one_strong_second_crop_keeps_the_original_prediction(self):
        whole = score("pizza", 0.03, relative_score=0.77)
        result = self.run_recognition(whole, {
            (0, 0, 0.55, 1): score("pizza", 0.06),
            (0, 0, 0.55, 0.55): score("pizza", 0.05),
            (0.45, 0, 1, 1): score("sushi", 0.06),
        })
        self.assertEqual(result["recognition_mode"], "single")
        self.assertEqual([dish["dish_name"] for dish in result["dishes"]], ["Pizza"])
        self.assertEqual(result["relative_score"], 0.77)

    def test_grid_regions_can_return_more_than_three_distinct_dishes(self):
        grid = _grid_windows()
        regional = {}
        for pair, label in zip((grid[0:2], grid[2:4], grid[4:6], grid[6:8]),
                               ("pizza", "sushi", "ramen", "hamburger")):
            regional.update({pair[0]: score(label, 0.05), pair[1]: score(label, 0.04)})

        result = self.run_recognition(score("pizza", 0.03), regional)

        self.assertEqual(result["recognition_mode"], "multi")
        self.assertEqual(
            {dish["dish_name"] for dish in result["dishes"]},
            {"Pizza", "Sushi", "Ramen", "Hamburger"},
        )

    def test_trace_explains_threshold_and_corroboration_rejections(self):
        grid = _grid_windows()
        traces = []
        result = self.run_recognition(score("pizza", 0.03), {
            grid[0]: score("pizza", 0.05),
            grid[1]: score("pizza", 0.04),
            grid[2]: score("sushi", 0.04),
            grid[4]: score("ramen", -0.01),
        })
        scores = [score("pizza", 0.03), *(
            {
                grid[0]: score("pizza", 0.05),
                grid[1]: score("pizza", 0.04),
                grid[2]: score("sushi", 0.04),
                grid[4]: score("ramen", -0.01),
            }.get(window, score("pasta", -0.02)) for window in _WINDOWS
        )]
        self.recognizer.score_features = lambda images: scores[:len(images)]
        recognize_meal(self.recognizer, self.image, trace=traces.append)

        self.assertEqual(result["recognition_mode"], "single")
        sushi = next(row for row in traces[0]["regions"] if row["winner"] == "sushi")
        ramen = next(row for row in traces[0]["regions"] if row["winner"] == "ramen")
        self.assertTrue(sushi["candidate"])
        self.assertFalse(sushi["corroborated"])
        self.assertIn("support_margin", ramen["filter_reasons"])

    def test_provisional_foods_outside_original_nine_can_form_a_meal(self):
        grid = _grid_windows()
        regional = {}
        for pair, label in zip((grid[0:2], grid[4:6], grid[12:14], grid[16:18]),
                               ("biryani", "fish and chips", "falafel", "cheesecake")):
            regional.update({pair[0]: provisional_score(label), pair[1]: provisional_score(label, 0.04)})

        result = self.run_recognition(score("pasta", -0.03), regional)

        self.assertEqual(result["recognition_mode"], "multi")
        self.assertEqual(
            {dish["dish_name"] for dish in result["dishes"]},
            {"Biryani", "Fish And Chips", "Falafel", "Cheesecake"},
        )
        self.assertFalse(result["accepted"])

    def test_provisional_whole_image_does_not_expand_one_plate_into_many_dishes(self):
        grid = _grid_windows()
        result = self.run_recognition(provisional_score("pancakes"), {
            grid[0]: provisional_score("pancakes"),
            grid[1]: provisional_score("pancakes", 0.04),
            grid[2]: provisional_score("arepas"),
            grid[3]: provisional_score("arepas", 0.04),
        })

        self.assertEqual(result["recognition_mode"], "single")
        self.assertEqual([dish["dish_name"] for dish in result["dishes"]], ["Pancakes"])

    def test_adjacent_alternative_noodle_guesses_do_not_become_two_dishes(self):
        grid = _grid_windows()
        regional = {
            grid[0]: provisional_score("ramen", 0.06),
            grid[1]: provisional_score("ramen", 0.05),
            grid[2]: provisional_score("dan dan noodles", 0.055, "ramen"),
            grid[3]: provisional_score("dan dan noodles", 0.045, "ramen"),
        }

        result = self.run_recognition(provisional_score("ramen"), regional)

        self.assertEqual(result["recognition_mode"], "single")
        self.assertEqual([dish["dish_name"] for dish in result["dishes"]], ["Ramen"])
