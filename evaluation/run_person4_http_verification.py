"""Verify the running Flask server over HTTP with real models and error cases."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time

import requests


QUERIES = [
    "I want sushi with fresh fish.",
    "I want a sweet dessert, such as tiramisu or cheesecake.",
    "I love spicy, savory food with rich flavors.",
]


def timed_request(method, url, **kwargs):
    started = time.perf_counter()
    response = requests.request(method, url, timeout=200, **kwargs)
    seconds = time.perf_counter() - started
    try:
        body = response.json()
    except requests.exceptions.JSONDecodeError:
        body = {"text_prefix": response.text[:200]}
    return {
        "http_status": response.status_code,
        "seconds": seconds,
        "response": body,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:7860")
    parser.add_argument("--photo", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.photo) < 2:
        parser.error("provide at least two --photo paths")
    base = args.base_url.rstrip("/")

    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": base,
        "served_over_network": True,
        "actual_model_inference": True,
        "checks": {},
        "limitations": [
            "Loopback HTTP and browser checks are local, not public deployment tests.",
            "Two photos are a demo check, not a recognition-accuracy estimate.",
            "Recommendation results verify real inference and changing outputs, not human relevance.",
        ],
    }
    home_started = time.perf_counter()
    home = requests.get(base + "/", timeout=20)
    report["checks"]["home"] = {
        "http_status": home.status_code,
        "seconds": time.perf_counter() - home_started,
        "contains_original_ui_copy": "Every dish becomes part of" in home.text,
    }
    report["checks"]["status"] = timed_request("GET", base + "/api/status")
    report["checks"]["current_build_summary"] = timed_request(
        "GET", base + "/api/recommendation-summary"
    )

    recommendations = []
    for index, preference in enumerate(QUERIES):
        check = timed_request(
            "POST",
            base + "/api/recommend",
            json={"preference": preference, "top_n": 5},
        )
        check["preference"] = preference
        check["timing_kind"] = "cold request: model load + inference + HTTP" if index == 0 else "warm inference + HTTP"
        recommendations.append(check)
    report["checks"]["recommendations"] = recommendations
    report["checks"]["distinct_recommendation_lists"] = len({
        tuple((row["restaurant_name"], row["dish_name"]) for row in check["response"].get("results", []))
        for check in recommendations
    })

    photos = []
    for index, photo in enumerate(args.photo):
        raw = photo.read_bytes()
        with photo.open("rb") as stream:
            check = timed_request(
                "POST",
                base + "/api/recognize",
                files={"image": (photo.name, stream, "image/jpeg")},
            )
        check.update({
            "file_name": photo.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "timing_kind": "cold request: model load + inference + HTTP" if index == 0 else "warm inference + HTTP",
        })
        photos.append(check)
    report["checks"]["recognition_photos"] = photos

    report["checks"]["errors"] = {
        "empty_preference": timed_request(
            "POST", base + "/api/recommend", json={"preference": "   "}
        ),
        "dietary_request": timed_request(
            "POST",
            base + "/api/recommend",
            json={"preference": "I need gluten-free pasta"},
        ),
        "missing_image": timed_request("POST", base + "/api/recognize"),
        "invalid_image": timed_request(
            "POST",
            base + "/api/recognize",
            files={"image": ("invalid.jpg", b"not an image", "image/jpeg")},
        ),
        "oversized_upload": timed_request(
            "POST",
            base + "/api/recognize",
            files={"image": ("large.jpg", b"x" * (8 * 1024 * 1024 + 1), "image/jpeg")},
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "home": report["checks"]["home"],
        "distinct_recommendation_lists": report["checks"]["distinct_recommendation_lists"],
        "recognition_outputs": [check["response"].get("dish_name") for check in photos],
        "error_statuses": {name: check["http_status"] for name, check in report["checks"]["errors"].items()},
    }, indent=2))


if __name__ == "__main__":
    main()
