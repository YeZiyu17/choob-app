"""Recommendation contract tests using synthetic fixtures, never model downloads.

The embedder below returns a fixed unit vector for arithmetic checks. These
fixtures and scores are test inputs, not food-recommendation evaluation results.
"""
import math
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import app as backend


DIMENSION = 384  # all-MiniLM-L6-v2's sentence embedding dimension.
COUNT_COLUMNS = (
    "positive_count", "negative_count", "mixed_count", "neutral_count",
)


class FixedUnitEmbedder:
    instances = []

    def __init__(self, model_name, device="cpu", revision=None):
        self.model_name = model_name
        self.device = device
        self.revision = revision
        self.calls = []
        self.instances.append(self)

    def get_sentence_embedding_dimension(self):
        return DIMENSION

    def encode(self, texts, normalize_embeddings=True, convert_to_numpy=True):
        self.calls.append((texts, normalize_embeddings, convert_to_numpy))
        vectors = np.zeros((len(texts), DIMENSION), dtype=np.float32)
        vectors[:, 0] = 1.0
        return vectors


class _RecommendationFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.df = pd.DataFrame([
            {
                "restaurant_name": "Synthetic restaurant A",
                "dish_name_normalized": "fixture a",
                "positive_count": 0, "negative_count": 2,
                "mixed_count": 0, "neutral_count": 0, "review_count": 2,
            },
            {
                "restaurant_name": "Synthetic restaurant B",
                "dish_name_normalized": "fixture b",
                "positive_count": 2, "negative_count": 0,
                "mixed_count": 0, "neutral_count": 0, "review_count": 2,
            },
        ])
        self.embeddings = np.zeros((2, DIMENSION), dtype=np.float32)
        self.embeddings[0, 0] = 1.0
        self.embeddings[1, :2] = [0.99, math.sqrt(1.0 - 0.99 ** 2)]
        self.write_data()
        FixedUnitEmbedder.instances.clear()
        module = types.ModuleType("sentence_transformers")
        module.SentenceTransformer = FixedUnitEmbedder
        self.module_patch = patch.dict(sys.modules, {"sentence_transformers": module})
        self.data_patch = patch.object(backend, "DATA", self.directory)
        self.module_patch.start()
        self.data_patch.start()
        backend.load_recommender.cache_clear()

    def tearDown(self):
        backend.load_recommender.cache_clear()
        self.data_patch.stop()
        self.module_patch.stop()
        self.temporary.cleanup()

    def write_data(self, df=None, embeddings=None):
        (self.df if df is None else df).to_csv(
            self.directory / "choob_recommendation_data.csv", index=False,
        )
        np.save(
            self.directory / "choob_dish_embeddings.npy",
            self.embeddings if embeddings is None else embeddings,
            allow_pickle=False,
        )


class RecommendationLoadingTests(_RecommendationFixture):
    def test_manifest_detects_mixed_or_modified_export_pair(self):
        paths = [self.directory / "choob_recommendation_data.csv",
                 self.directory / "choob_dish_embeddings.npy"]
        manifest = {"output_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
        manifest["embedding_model_revision"] = "fixture-recorded-revision"
        (self.directory / "choob_recommendation_manifest.json").write_text(json.dumps(manifest))
        self.assertEqual(backend.load_recommender()[2].revision, "fixture-recorded-revision")
        changed = self.df.copy()
        changed.loc[0, "dish_name_normalized"] = "different valid fixture"
        self.write_data(df=changed)
        backend.load_recommender.cache_clear()
        with self.assertRaisesRegex(ValueError, "manifest"):
            backend.load_recommender()

    def test_valid_paired_export_loads_once_and_preserves_row_order(self):
        loaded, embeddings, model = backend.load_recommender()
        self.assertEqual(loaded["dish_name_normalized"].tolist(), ["fixture a", "fixture b"])
        np.testing.assert_allclose(embeddings, self.embeddings)
        self.assertEqual(model.model_name, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(model.device, "cpu")
        self.assertIs(backend.load_recommender()[2], model)
        self.assertEqual(len(FixedUnitEmbedder.instances), 1)

    def test_missing_files_and_missing_schema_are_rejected(self):
        npy = self.directory / "choob_dish_embeddings.npy"
        npy.unlink()
        with self.assertRaises(FileNotFoundError):
            backend.load_recommender()
        self.write_data(df=self.df.drop(columns=["review_count"]))
        with self.assertRaises(ValueError):
            backend.load_recommender()

    def test_empty_export_is_rejected(self):
        self.write_data(self.df.iloc[:0], np.empty((0, DIMENSION), dtype=np.float32))
        with self.assertRaises(ValueError):
            backend.load_recommender()

    def test_embeddings_require_matching_rows_rank_and_dimension(self):
        cases = {
            "row_count": np.zeros((3, DIMENSION), dtype=np.float32),
            "rank_one": np.ones(2, dtype=np.float32),
            "rank_three": np.zeros((2, 1, DIMENSION), dtype=np.float32),
            "wrong_dimension": np.zeros((2, DIMENSION - 1), dtype=np.float32),
        }
        for name, vectors in cases.items():
            with self.subTest(name=name):
                backend.load_recommender.cache_clear()
                self.write_data(embeddings=vectors)
                with self.assertRaises(ValueError):
                    backend.load_recommender()

    def test_embeddings_require_finite_unit_vectors(self):
        for name, value in [("nan", np.nan), ("infinity", np.inf), ("zero", 0.0), ("unnormalized", 2.0)]:
            with self.subTest(name=name):
                vectors = self.embeddings.copy()
                vectors[0, 0] = value
                backend.load_recommender.cache_clear()
                self.write_data(embeddings=vectors)
                with self.assertRaises(ValueError):
                    backend.load_recommender()

    def test_counts_require_finite_nonnegative_integers(self):
        for column in (*COUNT_COLUMNS, "review_count"):
            for name, value in [("negative", -1), ("fractional", 0.5), ("nan", np.nan), ("infinity", np.inf), ("text", "invalid")]:
                with self.subTest(column=column, name=name):
                    invalid = self.df.copy()
                    invalid[column] = invalid[column].astype(object)
                    invalid.loc[0, column] = value
                    backend.load_recommender.cache_clear()
                    self.write_data(df=invalid)
                    with self.assertRaises(ValueError):
                        backend.load_recommender()

    def test_review_count_must_equal_sentiment_count_total(self):
        invalid = self.df.copy()
        invalid.loc[0, "review_count"] = 999
        self.write_data(df=invalid)
        with self.assertRaises(ValueError):
            backend.load_recommender()

    def test_review_count_must_be_positive(self):
        invalid = self.df.copy()
        invalid.loc[0, [*COUNT_COLUMNS, "review_count"]] = 0
        self.write_data(df=invalid)
        with self.assertRaises(ValueError):
            backend.load_recommender()

    def test_restaurant_and_dish_names_must_be_present(self):
        for column in ("restaurant_name", "dish_name_normalized"):
            for value in ("", "   ", None):
                with self.subTest(column=column, value=value):
                    invalid = self.df.copy()
                    invalid.loc[0, column] = value
                    backend.load_recommender.cache_clear()
                    self.write_data(df=invalid)
                    with self.assertRaises(ValueError):
                        backend.load_recommender()

    def test_duplicate_restaurant_dish_pairs_are_rejected(self):
        invalid = self.df.copy()
        invalid.loc[1, ["restaurant_name", "dish_name_normalized"]] = invalid.loc[
            0, ["restaurant_name", "dish_name_normalized"],
        ].values
        self.write_data(df=invalid)
        with self.assertRaises(ValueError):
            backend.load_recommender()

    def test_business_id_distinguishes_same_named_restaurants(self):
        valid = self.df.copy()
        valid.loc[1, ["restaurant_name", "dish_name_normalized"]] = valid.loc[
            0, ["restaurant_name", "dish_name_normalized"],
        ].values
        valid["business_id"] = ["synthetic-business-a", "synthetic-business-b"]
        self.write_data(df=valid)
        loaded, _, _ = backend.load_recommender()
        self.assertEqual(len(loaded), 2)
        backend.load_recommender.cache_clear()
        valid["business_id"] = "synthetic-business-a"
        self.write_data(df=valid)
        with self.assertRaises(ValueError):
            backend.load_recommender()


class RecommendationApiTests(_RecommendationFixture):
    def setUp(self):
        super().setUp()
        self.app_config_patch = patch.dict(backend.app.config, {"TESTING": False, "PROPAGATE_EXCEPTIONS": False})
        self.app_config_patch.start()
        self.logger_patch = patch.object(backend.app.logger, "disabled", True)
        self.logger_patch.start()
        self.client = backend.app.test_client()

    def tearDown(self):
        self.logger_patch.stop()
        self.app_config_patch.stop()
        super().tearDown()

    def test_unverified_dietary_requests_do_not_return_semantic_meat_matches(self):
        for preference in ("I want a vegetarian meal with mushrooms and tofu.",
                           "vegan tacos", "I have a peanut allergy", "gluten-free pasta", "我想吃素食"):
            with self.subTest(preference=preference):
                response = self.client.post("/api/recommend", json={"preference": preference})
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("results", response.get_json())
        self.assertEqual(FixedUnitEmbedder.instances, [])

    def test_ranking_uses_similarity_and_smoothed_sentiment_with_correct_rows(self):
        response = self.client.post("/api/recommend", json={"preference": "  synthetic preference  ", "top_n": 2})
        self.assertEqual(response.status_code, 200)
        results = response.get_json()["results"]
        # A has higher semantic similarity, but B's sentiment improves its final rank.
        self.assertEqual([item["dish_name"] for item in results], ["Fixture B", "Fixture A"])
        self.assertEqual([item["restaurant_name"] for item in results], ["Synthetic restaurant B", "Synthetic restaurant A"])
        self.assertAlmostEqual(results[0]["score"], 0.9540, places=4)
        self.assertAlmostEqual(results[1]["score"], 0.8875, places=4)
        self.assertAlmostEqual(results[0]["similarity"], 0.99, places=4)
        self.assertEqual([item["review_count"] for item in results], [2, 2])
        self.assertEqual(FixedUnitEmbedder.instances[0].calls, [(["synthetic preference"], True, True)])

    def test_top_n_limits_results_and_default_can_exceed_available_rows(self):
        response = self.client.post("/api/recommend", json={"preference": "synthetic preference", "top_n": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["results"]), 1)
        response = self.client.post("/api/recommend", json={"preference": "synthetic preference"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()["results"]), 2)
        self.assertEqual(len(FixedUnitEmbedder.instances), 1)

    def test_integer_top_n_keeps_existing_one_to_ten_clamping(self):
        for requested, expected in ((0, 1), (-10, 1), (100, 2)):
            with self.subTest(requested=requested):
                response = self.client.post("/api/recommend", json={"preference": "synthetic preference", "top_n": requested})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.get_json()["results"]), expected)

    def test_non_object_json_returns_400_before_loading_model(self):
        for payload in ([1], "text", 42, True):
            with self.subTest(payload=payload):
                response = self.client.post("/api/recommend", json=payload)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(FixedUnitEmbedder.instances, [])

    def test_preference_requires_nonempty_bounded_string(self):
        for value in (None, "", "  ", "x" * 1001, 1, True, ["food"], {"food": "dish"}):
            with self.subTest(value=value):
                response = self.client.post("/api/recommend", json={"preference": value})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(FixedUnitEmbedder.instances, [])

    def test_top_n_requires_integer_not_bool_float_or_structured_json(self):
        for value in (True, False, 1.5, "2", None, [], {}):
            with self.subTest(value=value):
                response = self.client.post("/api/recommend", json={"preference": "synthetic preference", "top_n": value})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(FixedUnitEmbedder.instances, [])

    def test_missing_or_malformed_json_returns_400(self):
        for kwargs in ({}, {"data": "{broken", "content_type": "application/json"}):
            with self.subTest(kwargs=kwargs):
                response = self.client.post("/api/recommend", **kwargs)
                self.assertEqual(response.status_code, 400)

    def test_missing_data_returns_503_and_recovers_after_export_arrives(self):
        (self.directory / "choob_dish_embeddings.npy").unlink()
        response = self.client.post("/api/recommend", json={"preference": "synthetic preference"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.get_json())
        self.write_data()
        response = self.client.post("/api/recommend", json={"preference": "synthetic preference"})
        self.assertEqual(response.status_code, 200)

    def test_corrupt_export_returns_503_instead_of_nan_rankings(self):
        invalid = self.embeddings.copy()
        invalid[0, 0] = np.nan
        self.write_data(embeddings=invalid)
        response = self.client.post("/api/recommend", json={"preference": "synthetic preference"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.get_json())

    def test_invalid_query_embedding_returns_503(self):
        nan_vector = np.zeros((1, DIMENSION), dtype=np.float32)
        nan_vector[0, 0] = np.nan
        infinite_vector = np.zeros((1, DIMENSION), dtype=np.float32)
        infinite_vector[0, 0] = np.inf
        for name, vectors in (
            ("rank_one", np.ones(DIMENSION, dtype=np.float32)),
            ("multiple_queries", np.ones((2, DIMENSION), dtype=np.float32)),
            ("wrong_dimension", np.ones((1, DIMENSION - 1), dtype=np.float32)),
            ("nan", nan_vector), ("infinity", infinite_vector),
        ):
            with self.subTest(name=name), patch.object(FixedUnitEmbedder, "encode", return_value=vectors):
                response = self.client.post("/api/recommend", json={"preference": "synthetic preference"})
                self.assertEqual(response.status_code, 503)
                self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()
