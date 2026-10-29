"""Live export replacement checks with synthetic data and a mocked embedder."""
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np

import app as backend
import test_recommendation as fixtures


class RecommendationCacheVersionTests(fixtures._RecommendationFixture):
    def write_manifest(self, revision="fixture-version-a"):
        paths = [self.directory / "choob_recommendation_data.csv",
                 self.directory / "choob_dish_embeddings.npy"]
        manifest = {
            "embedding_model_revision": revision,
            "output_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in paths},
        }
        (self.directory / "choob_recommendation_manifest.json").write_text(json.dumps(manifest))

    def test_unchanged_manifest_loads_once(self):
        self.write_manifest()
        first = backend.load_recommender()
        self.assertIs(backend.load_recommender(), first)
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 1)
        self.assertEqual(backend.load_recommender.cache_info().maxsize, 1)
        self.assertEqual(backend.load_recommender.cache_info().currsize, 1)

    def test_new_manifest_serves_new_dataset_without_manual_cache_clear(self):
        self.write_manifest()
        client = backend.app.test_client()
        first = client.post("/api/recommend", json={"preference": "synthetic preference"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json()["results"][0]["dish_name"], "Fixture B")
        previous_model = backend.load_recommender()[2]

        changed = self.df.copy()
        changed["dish_name_normalized"] = ["updated a", "updated b"]
        vectors = self.embeddings[::-1].copy()
        self.write_data(df=changed, embeddings=vectors)
        self.write_manifest("fixture-version-b")

        second = client.post("/api/recommend", json={"preference": "synthetic preference"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual([row["dish_name"] for row in second.get_json()["results"]],
                         ["Updated B", "Updated A"])
        loaded, embeddings, model = backend.load_recommender()
        self.assertEqual(loaded["dish_name_normalized"].tolist(), ["updated a", "updated b"])
        np.testing.assert_allclose(embeddings, vectors)
        self.assertIsNot(model, previous_model)
        self.assertEqual(model.revision, "fixture-version-b")
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 2)

    def test_manifest_version_is_scoped_to_data_directory(self):
        self.write_manifest()
        first = backend.load_recommender()
        with tempfile.TemporaryDirectory() as directory:
            other = Path(directory)
            for path in self.directory.iterdir():
                (other / path.name).write_bytes(path.read_bytes())
            with patch.object(backend, "DATA", other):
                second = backend.load_recommender()
        self.assertIsNot(second, first)
        self.assertIsNot(second[2], first[2])
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 2)

    def test_legacy_exports_reload_when_files_change(self):
        first = backend.load_recommender()
        self.assertIs(backend.load_recommender(), first)
        changed = self.df.copy()
        changed["dish_name_normalized"] = ["new legacy a", "new legacy b"]
        self.write_data(df=changed)
        second = backend.load_recommender()
        self.assertEqual(second[0]["dish_name_normalized"].tolist(),
                         ["new legacy a", "new legacy b"])
        self.assertIsNot(second[2], first[2])
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 2)

    def test_new_manifest_still_validates_hashes_and_recovers_after_repair(self):
        self.write_manifest()
        backend.load_recommender()
        self.write_manifest("fixture-version-b")
        changed = self.df.copy()
        changed.loc[0, "dish_name_normalized"] = "changed without matching manifest"
        self.write_data(df=changed)
        with self.assertRaisesRegex(ValueError, "manifest"):
            backend.load_recommender()
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 1)
        self.write_manifest("fixture-version-b")
        self.assertEqual(backend.load_recommender()[0].iloc[0]["dish_name_normalized"],
                         "changed without matching manifest")
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 2)

    def test_new_manifest_still_validates_shape_before_loading_model(self):
        self.write_manifest()
        backend.load_recommender()
        self.write_data(embeddings=np.zeros((3, fixtures.DIMENSION), dtype=np.float32))
        self.write_manifest("fixture-version-b")
        with self.assertRaisesRegex(ValueError, "rows do not match"):
            backend.load_recommender()
        self.assertEqual(len(fixtures.FixedUnitEmbedder.instances), 1)
