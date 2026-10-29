"""Compare real recommendation artifacts with a frozen preference-query suite.

Examples (run from the repository root, with the MiniLM cache available):
    python evaluation/run_recommendation_comparison.py --baseline-dir /path/to/old/data \
        --baseline-only --output /private/path/baseline.json
    python evaluation/run_recommendation_comparison.py --baseline-dir /path/to/old/data \
        --baseline-report /private/path/baseline.json \
        --output evaluation/results/recommendation_comparison.json \
        --human-output evaluation/results/recommendation_human_review.csv

The isolated comparison uses the original app's 85% semantic / 15% sentiment
formula on BOTH datasets. Actual Flask responses are recorded separately, so
changes to serving filters cannot masquerade as effects of additional data.
No review text, reviewer IDs, human relevance labels or accuracy claims are
generated. This is a coverage, artifact-integrity and API behavior check.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SUITE_ID = "choob-preference-probe-2026-10-28-v1"
# Frozen before the expanded recommendation artifacts were built or inspected.
# The first five are the original real-model smoke-test preferences.
QUERIES = (
    ("original_cheesesteak", "I want a juicy cheesesteak with melted cheese."),
    ("original_sushi", "I want sushi with fresh fish."),
    ("original_mushroom", "I want a hearty mushroom dish."),
    ("original_dessert", "I want a sweet dessert, such as tiramisu or cheesecake."),
    ("original_spicy", "I love spicy, savory food with rich flavors."),
    ("vietnamese_pho", "I want Vietnamese pho with a fragrant beef broth and rice noodles."),
    ("thai_curry", "I want a spicy Thai curry with coconut milk."),
    ("indian_curry", "I want an Indian chicken curry with rich, aromatic spices."),
    ("ethiopian_injera", "I want Ethiopian injera with flavorful lentil and meat stews."),
    ("french_crepes", "I want French crepes with a sweet filling."),
    ("bbq_brisket", "I want smoky BBQ beef brisket."),
    ("japanese_ramen", "I want Japanese ramen with a rich broth and noodles."),
    ("chinese_spicy", "I want a spicy Chinese dish with chili and Sichuan pepper."),
    ("korean_bibimbap", "I want Korean bibimbap with rice, vegetables, and spicy sauce."),
    ("caribbean_jerk", "I want Caribbean jerk chicken with bold, spicy seasoning."),
)
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
COUNT_COLUMNS = ("positive_count", "negative_count", "mixed_count", "neutral_count")
EXPORTS = ("choob_recommendation_data.csv", "choob_dish_embeddings.npy")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def normalize_data_dir(path):
    path = Path(path).resolve()
    return path / "data" if (path / "data" / EXPORTS[0]).is_file() else path


def read_artifacts(data_dir):
    manifest_path = data_dir / "choob_recommendation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("embedding_model") != MODEL_ID or manifest.get("embedding_model_revision") != MODEL_REVISION:
        raise ValueError("Both datasets must use the frozen MiniLM model and revision")
    for name in EXPORTS:
        if digest(data_dir / name) != manifest.get("output_sha256", {}).get(name):
            raise ValueError(f"Export does not match manifest: {name}")
    df = pd.read_csv(data_dir / EXPORTS[0])
    vectors = np.load(data_dir / EXPORTS[1], allow_pickle=False)
    required = {"business_id", "restaurant_name", "dish_name_normalized", "dish_description", "review_count", *COUNT_COLUMNS}
    if not required.issubset(df.columns) or df.empty:
        raise ValueError("Nonempty recommendation CSV with all scoring fields required")
    if vectors.shape != (len(df), 384) or not np.issubdtype(vectors.dtype, np.floating):
        raise ValueError("Recommendation vectors must be floating-point and aligned with CSV rows")
    if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-3):
        raise ValueError("Finite unit-normalized recommendation vectors required")
    if df.duplicated(["business_id", "dish_name_normalized"]).any():
        raise ValueError("Duplicate restaurant-dish keys")
    for column in COUNT_COLUMNS + ("review_count",):
        values = pd.to_numeric(df[column], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any() or (values != np.floor(values)).any():
            raise ValueError("Counts must be finite nonnegative integers")
    if (df.review_count < 1).any() or not np.array_equal(df[list(COUNT_COLUMNS)].sum(axis=1), df.review_count):
        raise ValueError("Review support must equal the sum of sentiment counts")
    if "row_index" in df and not np.array_equal(df.row_index.to_numpy(), np.arange(len(df))):
        raise ValueError("CSV row_index does not match vector order")
    return df, vectors, manifest


def dataset_summary(df, vectors, manifest, data_dir):
    support = df.review_count.to_numpy(dtype=int)
    cuisine_counts = None
    if "cuisine_group" in df:
        groups = df[["business_id", "cuisine_group"]].drop_duplicates()
        if groups.business_id.duplicated().any():
            raise ValueError("Conflicting cuisine labels for a restaurant")
        cuisine_counts = {str(k): int(v) for k, v in groups.cuisine_group.fillna("Unknown").value_counts().sort_index().items()}
    return {
        "reviews_processed": manifest.get("selected_reviews", manifest.get("input_reviews")),
        "restaurants_in_input": manifest.get("selected_restaurants", manifest.get("input_restaurants")),
        "restaurants_with_recommendations": int(df.business_id.nunique()),
        "restaurant_dish_pairs": len(df),
        "review_dish_mentions": int(support.sum()),
        "single_review_pairs": int((support == 1).sum()),
        "single_review_pair_fraction": float((support == 1).mean()),
        "pairs_supported_by_at_least_two_reviews": int((support >= 2).sum()),
        "multiple_review_pair_fraction": float((support >= 2).mean()),
        "mean_reviews_per_pair": float(np.mean(support)),
        "median_reviews_per_pair": float(np.median(support)),
        "max_reviews_per_pair": int(np.max(support)),
        "review_support_histogram": {str(k): int(v) for k, v in pd.Series(support).value_counts().sort_index().items()},
        "cuisine_groups_of_recommendable_restaurants": cuisine_counts,
        "embedding_shape": list(vectors.shape),
        "manifest_sha256": digest(data_dir / "choob_recommendation_manifest.json"),
        "export_sha256": {name: digest(data_dir / name) for name in EXPORTS},
        "extraction_route": manifest.get("extraction_route"),
        "extraction_model": manifest.get("extraction_model"),
        "failed_reviews": manifest.get("failed_reviews"),
        "review_status_counts": manifest.get("review_status_counts"),
    }


def isolated_ranking(df, vectors, query_vectors):
    positive, negative, mixed, neutral = [df[c].to_numpy(dtype=float) for c in COUNT_COLUMNS]
    support = positive + negative + mixed + neutral
    sentiment = (positive + 0.5 * mixed + 0.5 * neutral + 1) / (support + 2)
    checks = []
    for (query_id, preference), query_vector in zip(QUERIES, query_vectors):
        started = time.perf_counter()
        similarity = vectors @ query_vector
        scores = 0.85 * similarity + 0.15 * sentiment
        positions = np.argsort(-scores, kind="stable")[:5]
        elapsed = time.perf_counter() - started
        results = []
        for idx in positions:
            row = df.iloc[int(idx)]
            results.append({
                "business_id": str(row.business_id),
                "restaurant_name": str(row.restaurant_name),
                "dish_name": str(row.dish_name_normalized).title(),
                "review_count": int(row.review_count),
                "score": round(float(scores[idx]), 4),
                "similarity": round(float(similarity[idx]), 4),
                **({"cuisine_group": str(row.cuisine_group)} if "cuisine_group" in df else {}),
            })
        checks.append({"query_id": query_id, "preference": preference,
            "ranking_only_seconds": elapsed, "results": results})
    return checks


def latency_summary(values):
    return {"requests": len(values), "min_seconds": float(np.min(values)),
        "median_seconds": float(np.median(values)), "p95_seconds": float(np.percentile(values, 95)),
        "max_seconds": float(np.max(values))}


def api_checks(app_path, label, df, vectors, model, isolated):
    """Use each saved app's real routes and model, with its artifact loader supplied.

    Supplying the already-validated artifact bundle keeps old and current datasets
    isolated without writing either app's data directory or downloading weights.
    This is not a network/browser or cold-start benchmark.
    """
    if not app_path.is_file():
        return {"available": False, "reason": "No app.py beside the specified data directory"}
    sys.path.insert(0, str(app_path.parent))
    try:
        spec = importlib.util.spec_from_file_location(f"choob_comparison_{label}", app_path)
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
    finally:
        sys.path.pop(0)
    api_df = df.copy()
    backend.load_recommender = lambda: (api_df, vectors, model)
    client = backend.app.test_client()
    actual = []
    matches = []
    for query, reference in zip(QUERIES, isolated):
        query_id, preference = query
        started = time.perf_counter()
        response = client.post("/api/recommend", json={"preference": preference, "top_n": 5})
        elapsed = time.perf_counter() - started
        payload = response.get_json()
        if response.status_code != 200 or not isinstance(payload, dict) or len(payload.get("results", [])) != 5:
            raise AssertionError(f"Real-model API probe failed: {query_id}: {response.status_code}: {payload}")
        observed = payload["results"]
        scores = [item["score"] for item in observed]
        if not np.isfinite(scores).all() or scores != sorted(scores, reverse=True):
            raise AssertionError("API returned nonfinite or unsorted scores")
        for item in observed:
            rows = df[(df.restaurant_name == item["restaurant_name"]) & (df.dish_name_normalized.str.title() == item["dish_name"])]
            if rows.empty or item["review_count"] not in rows.review_count.tolist():
                raise AssertionError("API returned an item outside the artifact bundle")
        match = [(r["restaurant_name"], r["dish_name"], r["score"]) for r in observed] == [
            (r["restaurant_name"], r["dish_name"], r["score"]) for r in reference["results"]]
        matches.append(match)
        actual.append({"query_id": query_id, "preference": preference,
            "http_status": response.status_code, "warm_request_seconds": elapsed,
            "matches_isolated_85_15_ranking": match, "response": payload})
    invalid_cases = (
        ("json_array", ["invalid JSON shape"], 400),
        ("missing_preference", {}, 400),
        ("empty_preference", {"preference": "  "}, 400),
        ("overlong_preference", {"preference": "x" * 1001}, 400),
        ("noninteger_top_n", {"preference": "sushi", "top_n": 2.5}, 400),
        ("boolean_top_n", {"preference": "sushi", "top_n": True}, 400),
        ("unverified_dietary_request", {"preference": "I want a vegetarian meal with mushrooms and tofu."}, 422),
    )
    validation = []
    for name, payload, expected in invalid_cases:
        response = client.post("/api/recommend", json=payload)
        if response.status_code != expected or "results" in response.get_json():
            raise AssertionError(f"API validation changed: {name}: {response.status_code}")
        validation.append({"case": name, "http_status": response.status_code, "expected_http_status": expected})
    return {"available": True, "app_sha256": digest(app_path),
        "real_model_inference": True, "flask_test_client": True, "served_over_network": False,
        "artifact_loader_supplied_by_evaluator": True,
        "checks": actual, "validation_checks": validation,
        "all_rankings_match_isolated_formula": all(matches),
        "warm_latency": latency_summary([item["warm_request_seconds"] for item in actual]),
        "timing_scope": "One measured request per query; excludes startup, model loading, network, browser rendering. Descriptive timings, not a controlled performance benchmark."}


def evaluate_dataset(data_dir, label, model, query_vectors):
    df, vectors, manifest = read_artifacts(data_dir)
    positions = sorted({0, len(df) // 2, len(df) - 1})
    regenerated = model.encode(df.iloc[positions].dish_description.tolist(),
        normalize_embeddings=True, convert_to_numpy=True)
    difference = float(np.max(np.abs(regenerated - vectors[positions])))
    if difference >= 1e-5:
        raise AssertionError("Saved description embeddings failed alignment spot check")
    isolated = isolated_ranking(df, vectors, query_vectors)
    return {"dataset": dataset_summary(df, vectors, manifest, data_dir),
        "alignment_spot_rows": positions, "regenerated_embedding_max_difference": difference,
        "isolated_same_formula_checks": isolated,
        "api": api_checks(data_dir.parent / "app.py", label, df, vectors, model, isolated)}, df


def comparison_summary(baseline, current, old_df, new_df):
    keys = lambda df: set(zip(df.business_id.astype(str), df.dish_name_normalized.astype(str)))
    old_keys, new_keys = keys(old_df), keys(new_df)
    changes = []
    for before, after in zip(baseline["isolated_same_formula_checks"], current["isolated_same_formula_checks"]):
        before_keys = [(r["business_id"], r["dish_name"]) for r in before["results"]]
        after_keys = [(r["business_id"], r["dish_name"]) for r in after["results"]]
        changes.append({"query_id": before["query_id"], "top_five_order_changed": before_keys != after_keys,
            "shared_top_five_pairs": len(set(before_keys) & set(after_keys)),
            "newly_recommendable_top_five_pairs": sum((r["business_id"], r["dish_name"].lower()) not in old_keys for r in after["results"])})
    return {"restaurant_dish_pairs_added": len(new_keys - old_keys),
        "restaurant_dish_pairs_removed_or_renamed": len(old_keys - new_keys),
        "restaurant_dish_pair_keys_retained": len(old_keys & new_keys),
        "queries_with_changed_top_five_order": sum(r["top_five_order_changed"] for r in changes),
        "query_changes": changes,
        "interpretation": "Added coverage, review support and changed rankings are objective properties. They do not establish improved human relevance or accuracy. App responses may also reflect serving-logic changes; the isolated comparison holds the scoring formula fixed."}


def human_rows(report):
    for label in ("baseline", "current"):
        if label not in report:
            continue
        api = report[label]["api"]
        checks = api["checks"] if api.get("available") else report[label]["isolated_same_formula_checks"]
        for check in checks:
            results = check["response"]["results"] if api.get("available") else check["results"]
            for rank, item in enumerate(results, 1):
                yield {"system": label, "ranking_source": "actual_flask_response" if api.get("available") else "isolated_same_85_15_formula",
                    "query_id": check["query_id"], "preference": check["preference"], "rank": rank,
                    "dish_name": item["dish_name"], "restaurant_name": item["restaurant_name"],
                    "review_count": item["review_count"], "human_relevant_yes_no": "", "human_reason": ""}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", required=True, type=Path)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--baseline-only", action="store_true", help="Capture old artifacts before rebuilding")
    parser.add_argument("--baseline-report", type=Path, help="Verify the old results still match an earlier frozen report")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--human-output", type=Path)
    parser.add_argument("--allow-downloads", action="store_true", help="Default: use only cached pinned model weights")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for path in (args.output, args.human_output):
        if path and path.exists() and not args.overwrite:
            parser.error(f"Refusing to overwrite {path}; use a distinct output or --overwrite")
    query_suite = {"id": SUITE_ID, "frozen_date": "2026-10-28", "queries": [
        {"query_id": query_id, "preference": preference} for query_id, preference in QUERIES]}
    query_suite["sha256"] = json_digest(query_suite)
    from sentence_transformers import SentenceTransformer
    started = time.perf_counter()
    model = SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device="cpu",
        local_files_only=not args.allow_downloads)
    loading_seconds = time.perf_counter() - started
    started = time.perf_counter()
    query_vectors = model.encode([q for _, q in QUERIES], normalize_embeddings=True,
        convert_to_numpy=True).astype(np.float32)
    query_encoding_seconds = time.perf_counter() - started
    if query_vectors.shape != (len(QUERIES), 384) or not np.isfinite(query_vectors).all():
        raise AssertionError("Invalid real MiniLM query embeddings")
    baseline, old_df = evaluate_dataset(normalize_data_dir(args.baseline_dir), "baseline", model, query_vectors)
    if args.baseline_report:
        frozen = json.loads(args.baseline_report.read_text(encoding="utf-8"))
        if frozen["query_suite"] != query_suite or frozen["baseline"]["dataset"] != baseline["dataset"]:
            raise AssertionError("Frozen baseline query suite or artifacts changed")
        for before, after in zip(frozen["baseline"]["isolated_same_formula_checks"], baseline["isolated_same_formula_checks"]):
            if before["results"] != after["results"]:
                raise AssertionError("Frozen baseline rankings changed")
    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
        "query_suite": query_suite, "embedding_model": MODEL_ID,
        "embedding_model_revision": MODEL_REVISION, "device": "cpu",
        "actual_model_inference": True, "same_query_vectors_used_for_both_datasets": not args.baseline_only,
        "query_vectors_sha256": hashlib.sha256(query_vectors.tobytes()).hexdigest(),
        "model_loading_seconds": loading_seconds, "shared_query_encoding_seconds": query_encoding_seconds,
        "evaluator_sha256": digest(__file__),
        "isolated_ranking": {"semantic_weight": 0.85, "sentiment_weight": 0.15,
            "sentiment_formula": "(positive + 0.5*mixed + 0.5*neutral + 1)/(positive+negative+mixed+neutral+2)",
            "tie_breaking": "stable CSV row order", "top_n": 5},
        "baseline": baseline,
        "human_relevance_evaluation_completed": False,
        "limitations": [
            "Fifteen fixed probes check coverage, ranking changes, artifact integrity and API behavior; they are not a representative recommendation-quality test set.",
            "Human relevance and extraction-accuracy evaluation are pending. Blank reviewer columns must be completed by real reviewers.",
            "Additional data, more review support, larger scores or changed top-five lists do not prove that recommendations improved.",
            "Scores are uncalibrated ranking values, not probabilities of liking a dish.",
            "Historical sampled reviews do not verify current menus, business status, ingredients, diets or allergies.",
            "Timing excludes startup/model loading and network/browser costs; a single request per query is not a controlled latency benchmark.",
        ]}
    if not args.baseline_only:
        current, new_df = evaluate_dataset(normalize_data_dir(args.data_dir), "current", model, query_vectors)
        report["current"] = current
        report["comparison"] = comparison_summary(baseline, current, old_df, new_df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.human_output:
        rows = list(human_rows(report))
        args.human_output.parent.mkdir(parents=True, exist_ok=True)
        with args.human_output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({"report": str(args.output), "query_count": len(QUERIES),
        "baseline_rows": len(old_df), "current_rows": report.get("current", {}).get("dataset", {}).get("restaurant_dish_pairs"),
        "human_relevance_evaluation_completed": False}, indent=2))


if __name__ == "__main__":
    main()
