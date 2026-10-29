"""Synthetic build-contract checks; no downloads or model-quality claims."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

import build_recommendations as builder


class BuildMetadataTests(unittest.TestCase):
    def test_cuisine_metadata_changes_description_without_fabricating_taste(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restaurants.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["business_id", "name", "cuisine_group", "city", "is_open"])
                writer.writeheader()
                writer.writerow(dict(business_id="fixture", name="Synthetic", cuisine_group="Vietnamese", city="Philadelphia", is_open="0"))
            rows = [dict(business_id="fixture", dish_description="pho. Taste: not specified")]
            coverage = builder.enrich_restaurant_metadata(rows, path)
            self.assertEqual(coverage, {"Vietnamese": 1})
            self.assertEqual(rows[0]["dish_description"], "pho. Taste: not specified. Cuisine: Vietnamese")
            self.assertEqual(rows[0]["historical_is_open"], "0")

    def test_no_restaurant_file_preserves_legacy_description(self):
        rows = [dict(dish_description="fixture")]
        self.assertEqual(builder.enrich_restaurant_metadata(rows, None), {})
        self.assertEqual(rows, [dict(dish_description="fixture")])

    def test_catalog_group_does_not_add_unmentioned_menu_items_to_description(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "restaurants.csv"
            path.write_text('business_id,name,cuisine_group\nfixture,Synthetic,Japanese/Sushi/Ramen\n')
            rows = [dict(business_id="fixture", dish_description="teriyaki chicken. Taste: not specified")]
            builder.enrich_restaurant_metadata(rows, path)
            self.assertEqual(rows[0]["cuisine_group"], "Japanese/Sushi/Ramen")
            self.assertEqual(rows[0]["dish_description"], "teriyaki chicken. Taste: not specified. Cuisine: Japanese")

    def test_explicit_provenance_is_bound_to_source_and_review_count(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reviews.csv"
            source.write_text("synthetic input")
            metadata = dict(extraction_route="mixed_codex_local_qwen_mlx", extraction_model="Synthetic models",
                            source_sha256=builder.sha256_file(source), review_counts={"reused": 1, "new": 2})
            path = Path(directory) / "provenance.json"
            path.write_text(json.dumps(metadata))
            self.assertEqual(builder.read_annotation_provenance(path, source, 3), metadata)
            with self.assertRaisesRegex(ValueError, "counts"):
                builder.read_annotation_provenance(path, source, 4)
            source.write_text("changed input")
            with self.assertRaisesRegex(ValueError, "different review inputs"):
                builder.read_annotation_provenance(path, source, 3)

    def test_unknown_provenance_route_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "provenance.json"
            path.write_text(json.dumps(dict(extraction_route="invented")))
            with self.assertRaisesRegex(ValueError, "Unknown"):
                builder.read_annotation_provenance(path, path, 0)


if __name__ == "__main__":
    unittest.main()
