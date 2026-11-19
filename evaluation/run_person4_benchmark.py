"""Measure real local model loading and inference without changing saved team results."""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import statistics
import time

from PIL import Image, ImageOps

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app as backend


QUERIES = [
    "I want sushi with fresh fish.",
    "I want a sweet dessert, such as tiramisu or cheesecake.",
    "I love spicy, savory food with rich flavors.",
]


def elapsed(callable_):
    started = time.perf_counter()
    value = callable_()
    return value, time.perf_counter() - started


def summary(values):
    return {
        "n": len(values),
        "seconds": values,
        "mean_seconds": statistics.fmean(values),
        "median_seconds": statistics.median(values),
    }


def package_versions():
    names = [
        "numpy", "torch", "transformers", "sentence-transformers",
        "flask", "gunicorn", "pandas", "pillow", "requests",
    ]
    return {name: importlib.metadata.version(name) for name in names}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--photo", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.photo) < 2:
        parser.error("provide at least two --photo paths")

    manifest_path = ROOT / "data/choob_recommendation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "actual_model_inference": True,
        "served_over_network": False,
        "platform": {
            "machine": platform.machine(),
            "macos": platform.mac_ver()[0],
            "python": platform.python_version(),
        },
        "packages": package_versions(),
        "download_seconds": None,
        "download_note": "Models were already cached; download time was not measured.",
        "recommendation_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "recommendation_build": {
            "rows": manifest["recommendation_rows"],
            "restaurants": manifest["restaurants_with_recommendations"],
            "embedding_model": manifest["embedding_model"],
            "embedding_model_revision": manifest["embedding_model_revision"],
        },
    }

    backend.load_recommender.cache_clear()
    (df, embeddings, model), load_seconds = elapsed(backend.load_recommender)
    recommendation_checks = []
    inference_times = []
    for query in QUERIES:
        vector, seconds = elapsed(
            lambda query=query: model.encode(
                [query], normalize_embeddings=True, convert_to_numpy=True,
            )
        )
        inference_times.append(seconds)
        similarity = embeddings @ vector[0]
        top_index = int(similarity.argmax())
        recommendation_checks.append({
            "preference": query,
            "seconds": seconds,
            "top_semantic_dish": str(df.iloc[top_index]["dish_name_normalized"]),
            "top_semantic_restaurant": str(df.iloc[top_index]["restaurant_name"]),
        })
    report["recommendation"] = {
        "artifact_and_model_load_seconds": load_seconds,
        "first_inference_seconds": inference_times[0],
        "subsequent_inference": summary(inference_times[1:]),
        "checks": recommendation_checks,
        "note": "Direct MiniLM encode timing; ranking API also adds data scoring and JSON serialization.",
    }
    backend.load_recommender.cache_clear()
    del df, embeddings, model
    gc.collect()

    backend.get_recognizer.cache_clear()
    backend.get_clip.cache_clear()
    recognizer, clip_load_seconds = elapsed(backend.get_recognizer)
    recognition_checks = []
    inference_times = []
    for photo_path in args.photo:
        raw = photo_path.read_bytes()
        with Image.open(photo_path) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
        predictions = []
        for run in range(3):
            prediction, seconds = elapsed(lambda image=image: recognizer.predict(image))
            inference_times.append(seconds)
            predictions.append({"run": run + 1, "seconds": seconds, "response": prediction})
        recognition_checks.append({
            "file_name": photo_path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "size": list(image.size),
            "runs": predictions,
        })
    report["recognition"] = {
        "model": "openai/clip-vit-base-patch32",
        "recognizer_model_and_prompt_cache_load_seconds": clip_load_seconds,
        "first_inference_seconds": inference_times[0],
        "subsequent_inference": summary(inference_times[1:]),
        "checks": recognition_checks,
        "note": "Two external photos, three sequential predictions each; this is a demo check, not an accuracy estimate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "recommendation_artifact_and_model_load_seconds": load_seconds,
        "clip_recognizer_load_seconds": clip_load_seconds,
        "recognition_outputs": [
            check["runs"][0]["response"]["dish_name"] for check in recognition_checks
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
