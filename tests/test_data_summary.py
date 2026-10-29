"""Build-summary contract tests; these do not download or evaluate AI models."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app as backend


class RecommendationSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.manifest_path = self.directory / "choob_recommendation_manifest.json"
        self.manifest = {
            "input_reviews": 12, "selected_reviews": 10,
            "input_restaurants": 4, "selected_restaurants": 3,
            "restaurant_catalog_size": 20, "restaurants_with_recommendations": 2,
            "extracted_review_dish_records": 9, "recommendation_rows": 7,
            "failed_reviews": 1,
            "review_status_counts": {"processed": 6, "zero_dishes": 2,
                                     "no_eligible_dishes": 1, "failed": 1},
            "source_sha256": "a" * 64, "config_sha256": "b" * 64,
            "created_utc": "2026-10-28T12:00:00+00:00",
            "extraction_route": "fixture_route", "extraction_model": "Fixture/model",
            "embedding_model": "Fixture/embedder", "human_evaluation_completed": False,
        }
        self.data_patch = patch.object(backend, "DATA", self.directory)
        self.data_patch.start()
        self.client = backend.app.test_client()
        self.write_manifest()

    def tearDown(self):
        self.data_patch.stop()
        self.temporary.cleanup()

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_summary_is_readable_without_models_or_export_files(self):
        with patch.object(backend, "load_recommender", side_effect=AssertionError("Model loaded")), \
                patch.object(backend, "get_clip", side_effect=AssertionError("Model loaded")):
            response = self.client.get("/api/recommendation-summary")
        self.assertEqual(response.status_code, 200)
        summary = response.get_json()
        self.assertEqual(summary["selected_reviews"], 10)
        self.assertEqual(summary["zero_dish_reviews"], 3)
        self.assertEqual(summary["failed_reviews"], 1)
        self.assertEqual(summary["build_version"], "b" * 12)
        self.assertEqual(summary["source_version"], "a" * 12)
        self.assertEqual(summary["manifest_sha256"], hashlib.sha256(self.manifest_path.read_bytes()).hexdigest())
        self.assertIs(summary["human_evaluation_completed"], False)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_new_manifest_is_read_on_the_next_request(self):
        first = self.client.get("/api/recommendation-summary").get_json()
        self.manifest["config_sha256"] = "c" * 64
        self.manifest["human_evaluation_completed"] = True
        self.write_manifest()
        second = self.client.get("/api/recommendation-summary").get_json()
        self.assertNotEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual(second["build_version"], "c" * 12)
        self.assertIs(second["human_evaluation_completed"], True)

    def test_private_extra_fields_are_not_returned(self):
        self.manifest.update(private_path="/private/fixture", review_id="private-id",
                             notes="private note", raw_review="private review")
        self.write_manifest()
        response = self.client.get("/api/recommendation-summary")
        self.assertEqual(response.status_code, 200)
        for value in ("/private/fixture", "private-id", "private note", "private review"):
            self.assertNotIn(value, response.get_data(as_text=True))

    def test_missing_manifest_returns_unavailable_not_zero_counts(self):
        self.manifest_path.unlink()
        response = self.client.get("/api/recommendation-summary")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(set(response.get_json()), {"error"})

    def test_malformed_manifest_returns_unavailable(self):
        for content in ("not-json", "[]", "null", '{"input_reviews": 12}'):
            with self.subTest(content=content):
                self.manifest_path.write_text(content, encoding="utf-8")
                response = self.client.get("/api/recommendation-summary")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(set(response.get_json()), {"error"})

    def test_inconsistent_status_totals_are_rejected(self):
        self.manifest["review_status_counts"]["processed"] = 5
        self.write_manifest()
        self.assertEqual(self.client.get("/api/recommendation-summary").status_code, 503)

    def test_optional_catalog_is_reported_as_unknown(self):
        self.manifest["restaurant_catalog_size"] = None
        self.write_manifest()
        response = self.client.get("/api/recommendation-summary")
        self.assertEqual(response.status_code, 200)
        summary = response.get_json()
        self.assertIsNone(summary["restaurant_catalog_size"])
        self.assertEqual(summary["input_restaurants"], 4)
        self.assertEqual(summary["restaurants_with_recommendations"], 2)

    def test_catalog_count_must_be_unknown_or_a_consistent_nonnegative_integer(self):
        for value in (-1, True, "20", 3):
            with self.subTest(value=value):
                self.manifest["restaurant_catalog_size"] = value
                self.write_manifest()
                self.assertEqual(self.client.get("/api/recommendation-summary").status_code, 503)

    def test_unknown_catalog_does_not_relax_other_count_checks(self):
        self.manifest["restaurant_catalog_size"] = None
        for key, value in (("input_reviews", None), ("input_restaurants", 2),
                           ("selected_reviews", -1), ("recommendation_rows", 100)):
            with self.subTest(key=key, value=value):
                original = self.manifest[key]
                self.manifest[key] = value
                self.write_manifest()
                self.assertEqual(self.client.get("/api/recommendation-summary").status_code, 503)
                self.manifest[key] = original

    def test_invalid_counts_and_flags_are_rejected(self):
        for key, value in (("input_reviews", True), ("failed_reviews", -1),
                           ("recommendation_rows", 100), ("human_evaluation_completed", "false")):
            with self.subTest(key=key):
                original = self.manifest[key]
                self.manifest[key] = value
                self.write_manifest()
                self.assertEqual(self.client.get("/api/recommendation-summary").status_code, 503)
                self.manifest[key] = original

    def test_invalid_hash_date_or_path_metadata_is_rejected(self):
        for key, value in (("source_sha256", "not-a-hash"),
                           ("created_utc", "2026-10-28T12:00:00"),
                           ("extraction_model", "/private/fixture/model")):
            with self.subTest(key=key):
                original = self.manifest[key]
                self.manifest[key] = value
                self.write_manifest()
                response = self.client.get("/api/recommendation-summary")
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(value, response.get_data(as_text=True))
                self.manifest[key] = original


if __name__ == "__main__":
    unittest.main()
