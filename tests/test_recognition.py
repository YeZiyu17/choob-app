"""Regression checks for abstention and configuration, without weight downloads."""
import json
from pathlib import Path
import tempfile
import unittest

from recognition import DishRecognizer, load_threshold, vocabulary_fingerprint


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

    def test_high_relative_score_does_not_override_out_of_scope(self):
        result = self.recognizer.predict_from_scores(self.scores)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["dish_name"], "Unknown")
        self.assertEqual(result["suggested_dish"], "Pizza")
        self.assertEqual(result["cuisine"], "Unknown")
        self.assertTrue(result["needs_user_confirmation"])

    def test_threshold_boundary_is_consistent_with_calibration(self):
        result = self.recognizer.predict_from_scores({**self.scores, "support_margin": 0.02})
        self.assertTrue(result["accepted"])
        self.assertEqual(result["dish_name"], "Pizza")
        self.assertTrue(result["needs_user_confirmation"])

    def test_vocabulary_change_requires_recalibration(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "config.json"
            config.write_text(json.dumps({"vocabulary_fingerprint": "stale", "support_margin_threshold": 0.02}))
            with self.assertRaisesRegex(ValueError, "recalibrate"):
                load_threshold(config)
            config.write_text(json.dumps({"vocabulary_fingerprint": vocabulary_fingerprint(), "support_margin_threshold": float("nan")}))
            with self.assertRaisesRegex(ValueError, "threshold"):
                load_threshold(config)

    def test_shipped_configuration_matches_current_vocabulary(self):
        self.assertIsInstance(load_threshold(), float)


if __name__ == "__main__":
    unittest.main()
