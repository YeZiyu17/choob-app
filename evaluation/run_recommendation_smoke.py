"""Exercise the real recommendation artifacts and MiniLM through Flask's test client."""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app as backend


def main():
    started = time.perf_counter()
    df, embeddings, model = backend.load_recommender()
    loading_seconds = time.perf_counter() - started
    manifest_path = ROOT / "data/choob_recommendation_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert embeddings.shape == (len(df), 384)
    positions = sorted({0, len(df) // 2, len(df) - 1})
    regenerated = model.encode(df.iloc[positions]["dish_description"].tolist(),
        normalize_embeddings=True, convert_to_numpy=True)
    max_difference = float(np.max(np.abs(regenerated - embeddings[positions])))
    assert max_difference < 1e-5, "Saved embeddings are not aligned with descriptions"
    queries = [
        "I want a juicy cheesesteak with melted cheese.",
        "I want sushi with fresh fish.",
        "I want a hearty mushroom dish.",
        "I want a sweet dessert, such as tiramisu or cheesecake.",
        "I love spicy, savory food with rich flavors.",
    ]
    client = backend.app.test_client()
    checks = []
    for preference in queries:
        started = time.perf_counter()
        response = client.post("/api/recommend", json={"preference": preference, "top_n": 5})
        elapsed = time.perf_counter() - started
        payload = response.get_json()
        assert response.status_code == 200, payload
        assert len(payload["results"]) == 5
        scores = [row["score"] for row in payload["results"]]
        assert all(np.isfinite(scores)) and scores == sorted(scores, reverse=True)
        for item in payload["results"]:
            matching = df[(df.restaurant_name == item["restaurant_name"]) &
                          (df.dish_name_normalized.str.title() == item["dish_name"])]
            assert not matching.empty, "API returned an item outside the real dataset"
            assert item["review_count"] in matching.review_count.tolist()
        checks.append({"preference": preference, "http_status": response.status_code,
                       "warm_request_seconds": elapsed, **payload})
    distinct = len({tuple((r["restaurant_name"], r["dish_name"]) for r in c["results"])
                    for c in checks})
    assert distinct >= 3, "Different preferences did not change recommendations"
    invalid = client.post("/api/recommend", json=["invalid JSON shape"])
    assert invalid.status_code == 400
    dietary = client.post("/api/recommend", json={"preference": "I want a vegetarian meal with mushrooms and tofu."})
    assert dietary.status_code == 422 and "results" not in dietary.get_json()
    report = {
        "actual_model_inference": True, "flask_test_client": True,
        "served_over_network": False,
        "extraction_route": manifest["extraction_route"],
        "extraction_model": manifest["extraction_model"],
        "embedding_model": manifest["embedding_model"],
        "dataset_rows": len(df), "restaurants": int(df.business_id.nunique()),
        "embedding_shape": list(embeddings.shape),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "artifact_alignment_spot_rows": positions,
        "regenerated_embedding_max_difference": max_difference,
        "loading_seconds": loading_seconds,
        "different_top_five_lists": distinct,
        "invalid_json_shape_http_status": invalid.status_code,
        "unverified_dietary_request": {"http_status": dietary.status_code,
                                       "response": dietary.get_json()},
        "checks": checks,
        "limitations": [
            "This checks real inference, API integration and row alignment; it is not a recommendation relevance benchmark.",
            "Sampled historical reviews do not establish current menu availability, dietary safety or restaurant status.",
            "The manifest identifies the actual extraction route and any reused annotations; no model weights were fine-tuned.",
            "The semantic spot audit was performed by AI, not a human reviewer.",
            "Warm request timings exclude process startup, model loading, network and browser rendering.",
        ],
    }
    destination = ROOT / "evaluation/results/recommendation_smoke.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"rows": len(df), "restaurants": report["restaurants"],
                      "distinct_query_results": distinct,
                      "max_alignment_difference": max_difference,
                      "report": str(destination)}, indent=2))


if __name__ == "__main__":
    main()
