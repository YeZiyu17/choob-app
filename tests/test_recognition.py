"""Regression checks for calibrated acceptance and broad provisional suggestions."""
import json
from pathlib import Path
import tempfile
import unittest

from food_vocabulary import FOOD_CANDIDATES, FOOD_GROUPS
from recognition import (
    DishRecognizer,
    calibrated_vocabulary_fingerprint,
    load_recognition_config,
    load_threshold,
    vocabulary_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]


class ScopePolicyTests(unittest.TestCase):
    def setUp(self):
        self.recognizer = DishRecognizer.__new__(DishRecognizer)
        self.recognizer.threshold = 0.02
        self.recognizer.labels = ["pizza", "pasta", "dumplings"]
        self.scores = {
            "support_margin": -0.01,
            "top_3": [{"dish_name": "pizza", "relative_score": 0.99},
                      {"dish_name": "pasta", "relative_score": 0.009},
                      {"dish_name": "dumplings", "relative_score": 0.001}],
        }

    def test_high_relative_score_does_not_force_a_food_suggestion(self):
        result = self.recognizer.predict_from_scores(self.scores)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["reviewable"])
        self.assertEqual(result["dish_name"], "Unknown")
        self.assertEqual(result["suggestion_mode"], "no_useful_food_suggestion")
        self.assertTrue(result["needs_user_confirmation"])

    def test_broad_food_is_an_editable_provisional_suggestion(self):
        result = self.recognizer.predict_from_scores({
            **self.scores,
            "calibrated_accepted": False,
            "suggestion_useful": True,
            "suggestion_top_3": [
                {"dish_name": "biryani", "similarity": 0.31},
                {"dish_name": "BIRYANI", "similarity": 0.30},
                {"dish_name": "pulao", "similarity": 0.28},
            ],
            "review_label": "biryani",
            "review_mode": "provisional",
        })
        self.assertFalse(result["accepted"])
        self.assertTrue(result["reviewable"])
        self.assertEqual(result["dish_name"], "Biryani")
        self.assertEqual(result["status"], "suggestion")
        self.assertEqual(result["suggestion_mode"], "provisional_food_candidate")
        self.assertIn("not a probability", result["score_note"])
        self.assertEqual([row["dish_name"] for row in result["ranked_guesses"]], ["Biryani", "Pulao"])
        self.assertEqual(result["ranked_guesses"][0]["match_score"], 0.31)
        self.assertEqual(result["score_label"], "Match score")
        self.assertEqual(result["rank_scope"], "photo")

    def test_threshold_boundary_remains_scoped_to_frozen_nine_families(self):
        ranked = [
            {"dish_name": "pizza", "relative_score": 0.8, "match_score": 0.34},
            {"dish_name": "pasta", "relative_score": 0.15, "match_score": 0.29},
            {"dish_name": "dumplings", "relative_score": 0.05, "match_score": 0.25},
        ]
        result = self.recognizer.predict_from_scores({**self.scores, "top_3": ranked, "support_margin": 0.02})
        self.assertTrue(result["accepted"])
        self.assertEqual(result["dish_name"], "Pizza")
        self.assertEqual(result["suggestion_mode"], "calibrated_supported")
        self.assertEqual([row["dish_name"] for row in result["ranked_guesses"]],
                         ["Pizza", "Pasta", "Dumplings"])
        self.assertEqual(result["alternatives"], result["ranked_guesses"][1:])

    def test_configuration_rejects_stale_or_misrepresented_policies(self):
        shipped = json.loads((ROOT / "recognition_config.json").read_text())
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            stale = {**shipped, "vocabulary_fingerprint": "stale"}
            config.write_text(json.dumps(stale))
            with self.assertRaisesRegex(ValueError, "vocabulary changed"):
                load_recognition_config(config)

            invalid = json.loads(json.dumps(shipped))
            invalid["legacy_calibrated_gate"]["support_margin_threshold"] = float("nan")
            config.write_text(json.dumps(invalid))
            with self.assertRaisesRegex(ValueError, "threshold"):
                load_recognition_config(config)

            misrepresented = json.loads(json.dumps(shipped))
            misrepresented["expanded_suggestion_policy"]["calibration_status"] = "calibrated"
            config.write_text(json.dumps(misrepresented))
            with self.assertRaisesRegex(ValueError, "calibration status"):
                load_recognition_config(config)

    def test_shipped_configuration_separates_frozen_and_provisional_layers(self):
        config = load_recognition_config()
        self.assertEqual(config["vocabulary_fingerprint"], vocabulary_fingerprint())
        self.assertEqual(
            config["legacy_calibrated_gate"]["vocabulary_fingerprint"],
            calibrated_vocabulary_fingerprint(),
        )
        self.assertEqual(
            config["expanded_suggestion_policy"]["calibration_status"],
            "provisional_unvalidated",
        )
        self.assertIsInstance(load_threshold(), float)

    def test_structured_vocabulary_has_broad_candidate_coverage(self):
        self.assertGreaterEqual(len(FOOD_CANDIDATES), 350)
        for label in ("biryani", "fish and chips", "cheesecake", "bibimbap", "pho",
                      "falafel", "paella", "ceviche", "pancakes", "coffee"):
            self.assertIn(label, FOOD_CANDIDATES)
        self.assertTrue({"Chinese", "Japanese", "Korean", "Indian", "Southeast Asian",
                         "Middle Eastern & North African", "Italian & European",
                         "Latin American & Caribbean", "American & Canadian"}.issubset(FOOD_GROUPS))
        self.assertIn("chicken and rice", FOOD_CANDIDATES["arroz con pollo"]["aliases"])
        self.assertEqual(len(FOOD_CANDIDATES), len(set(FOOD_CANDIDATES)))


if __name__ == "__main__":
    unittest.main()
