"""Checks for regional agreement and the original recognition response."""
import unittest

from PIL import Image

from multi_dish import _WINDOWS, recognize_meal
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


class MultiDishPolicyTests(unittest.TestCase):
    def setUp(self):
        self.recognizer = DishRecognizer.__new__(DishRecognizer)
        self.recognizer.threshold = 0.005
        self.recognizer.labels = ["pizza", "sushi", "pasta", "ramen"]
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
