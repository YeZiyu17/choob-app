"""Predeclared calibration / fresh holdout comparison for Choob's CLIP recognizer.

Run in Colab with the existing CLIP model and processor already loaded:
    from recognition import DishRecognizer
    summary, records = run_comparison(model, processor)

This evaluates prompt / candidate / rejection changes, not trained model weights.
The final sample manifest is fixed before inference. The threshold is frozen on
calibration data before any holdout predictions are computed.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import math
import time

import requests
from PIL import Image

API = "https://datasets-server.huggingface.co"
DATASET = "ethz/food101"
SOURCE = "https://huggingface.co/datasets/ethz/food101"
BASELINE_CANDIDATES = [
    "tonkotsu ramen", "shoyu ramen", "sushi", "dumplings", "fried rice",
    "pad thai", "pizza", "pasta", "hamburger", "tacos",
]
SUPPORTED_GROUPS = [
    ("dumplings", "dumplings"), ("fried_rice", "fried rice"),
    ("hamburger", "hamburger"), ("pad_thai", "pad thai"),
    ("pizza", "pizza"), ("spaghetti_bolognese", "pasta"),
    ("sushi", "sushi"), ("tacos", "tacos"), ("ramen", "ramen"),
]
CALIBRATION_OOD = [
    "apple_pie", "chocolate_cake", "caesar_salad", "french_fries",
    "ice_cream", "steak", "pancakes", "hot_dog",
]
ADDITIONAL_HOLDOUT_OOD = [
    "baklava", "cheesecake", "chicken_wings", "club_sandwich",
    "cup_cakes", "falafel", "nachos", "waffles",
]
MIN_CALIBRATION_RECALL = 0.90


def _api_get(endpoint, **extra):
    """Retry the same preselected request; never replace a failing sample."""
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(
                API + endpoint,
                params={"dataset": DATASET, "config": "default",
                        "split": "validation", **extra},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Dataset request failed after 3 attempts: {endpoint}") from last_error


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def _sample_plan():
    """Offsets within each class block, fixed independently of predictions."""
    plan = []
    for partition, start in [("calibration", 20), ("holdout", 100)]:
        for source_label, expected in SUPPORTED_GROUPS:
            plan.append({
                "partition": partition, "dataset_label": source_label,
                "expected_label": expected,
                "case_type": "ramen_family_only" if expected == "ramen" else "in_scope",
                "ood_group": None, "class_offset": start, "count": 20,
            })
        for source_label in CALIBRATION_OOD:
            plan.append({
                "partition": partition, "dataset_label": source_label,
                "expected_label": None, "case_type": "out_of_scope",
                "ood_group": "calibration_seen_classes", "class_offset": start,
                "count": 10,
            })
    for source_label in ADDITIONAL_HOLDOUT_OOD:
        plan.append({
            "partition": "holdout", "dataset_label": source_label,
            "expected_label": None, "case_type": "out_of_scope",
            "ood_group": "additional_holdout_classes", "class_offset": 100,
            "count": 10,
        })
    return plan


def _download_samples(out):
    image_dir = out / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    first = _api_get("/first-rows")
    names = next(feature["type"]["names"] for feature in first["features"]
                 if feature["name"] == "label")
    if len(names) != 101 or len(set(names)) != 101:
        raise RuntimeError("Expected the documented Food-101 class schema")
    label_ids = {name: index for index, name in enumerate(names)}

    def inspect_block(block):
        data = _api_get("/rows", offset=block * 250, length=1)
        if len(data["rows"]) != 1:
            raise RuntimeError("Missing class block")
        entry = data["rows"][0]
        if entry["row_idx"] != block * 250:
            raise RuntimeError("Dataset row index differs from requested offset")
        return entry["row"]["label"], entry["row_idx"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        blocks = list(pool.map(inspect_block, range(101)))
    offsets = dict(blocks)
    if len(offsets) != 101 or set(offsets) != set(range(101)):
        raise RuntimeError("Validation rows no longer form 101 distinct 250-row class blocks")

    plan = _sample_plan()
    _write_json(out / "sampling_plan.json", {
        "created_utc": _utc_now(), "dataset": DATASET, "split": "validation",
        "minimum_calibration_recall": MIN_CALIBRATION_RECALL, "groups": plan,
    })

    def select_group(group):
        label_id = label_ids[group["dataset_label"]]
        start = offsets[label_id] + group["class_offset"]
        entries = _api_get("/rows", offset=start, length=group["count"])["rows"]
        expected_rows = list(range(start, start + group["count"]))
        if [entry["row_idx"] for entry in entries] != expected_rows:
            raise RuntimeError("Incomplete or reordered sample group: " + group["dataset_label"])
        if any(entry["row"]["label"] != label_id for entry in entries):
            raise RuntimeError("Unexpected ground truth label: " + group["dataset_label"])
        return [(group, entry) for entry in entries]

    with ThreadPoolExecutor(max_workers=4) as pool:
        selected = [item for group_rows in pool.map(select_group, plan) for item in group_rows]
    selected_ids = [entry["row_idx"] for _, entry in selected]
    if len(selected) != 600 or len(set(selected_ids)) != 600:
        raise RuntimeError("Expected exactly 600 distinct predeclared rows")
    print("Fixed 260 calibration and 340 holdout rows before inference.", flush=True)

    def download(item):
        group, entry = item
        path = image_dir / f"{group['dataset_label']}_{entry['row_idx']}.jpg"
        if path.exists():
            payload = path.read_bytes()
        else:
            last_error = None
            for attempt in range(3):
                try:
                    response = requests.get(entry["row"]["image"]["src"], timeout=60)
                    response.raise_for_status()
                    payload = response.content
                    break
                except requests.RequestException as error:
                    last_error = error
                    if attempt < 2:
                        time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Image download failed for row {entry['row_idx']}") from last_error
            path.write_bytes(payload)
        with Image.open(BytesIO(payload)) as original:
            original.verify()
        with Image.open(BytesIO(payload)) as original:
            image = original.convert("RGB")
        record = {
            "dataset": DATASET, "split": "validation", "row_idx": entry["row_idx"],
            **{key: value for key, value in group.items() if key not in {"count", "class_offset"}},
            "class_row_offset": entry["row_idx"] - offsets[label_ids[group["dataset_label"]]],
            "image_file": str(path.relative_to(out)),
            "image_sha256": sha256(payload).hexdigest(), "image_width": image.width,
            "image_height": image.height,
        }
        return image, record

    with ThreadPoolExecutor(max_workers=4) as pool:
        samples = list(pool.map(download, selected))
    hashes = [record["image_sha256"] for _, record in samples]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError("Duplicate image bytes detected; stop rather than substitute holdout samples")
    manifest = [record for _, record in samples]
    _write_json(out / "sample_manifest.json", manifest)
    print("Downloaded and verified every image; all 600 source rows and hashes are distinct.", flush=True)
    return samples


def _select_threshold(calibration_records, minimum_recall=MIN_CALIBRATION_RECALL):
    supported = [record for record in calibration_records if record["case_type"] != "out_of_scope"]
    margins = sorted((float(record["optimized_scores"]["support_margin"])
                      for record in supported), reverse=True)
    if not margins or any(not math.isfinite(value) for value in margins):
        raise ValueError("Calibration margins must be finite and nonempty")
    required = math.ceil(minimum_recall * len(margins))
    threshold = margins[required - 1]
    return threshold, {
        "rule": "Largest support-margin threshold retaining at least 90% of calibration in-scope images; acceptance uses margin >= threshold.",
        "required_supported_accepts": required, "supported_images": len(margins),
        "actual_supported_accepts": sum(value >= threshold for value in margins),
        "minimum_supported_recall": minimum_recall,
        "threshold": threshold,
        "ties": "All margins equal to the threshold are accepted; recall can exceed the target.",
    }


def _canonical_label(label):
    return "ramen" if label in {"tonkotsu ramen", "shoyu ramen"} else label


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


def _evaluate_records(records, system):
    supported = [row for row in records if row["case_type"] != "out_of_scope"]
    mapped = [row for row in supported if row["case_type"] == "in_scope"]
    ramen = [row for row in supported if row["case_type"] == "ramen_family_only"]
    ood = [row for row in records if row["case_type"] == "out_of_scope"]

    def correct(row, topk=1):
        names = [_canonical_label(item["dish_name"]) for item in row[system]["top_3"][:topk]]
        return row["expected_label"] in names

    accepted = [row for row in records if row[system]["accepted"]]
    supported_accepted = [row for row in supported if row[system]["accepted"]]
    correct_accepted = sum(correct(row) for row in supported_accepted)
    ood_accepted = sum(row[system]["accepted"] for row in ood)
    per_category = {}
    for source_label in sorted({row["dataset_label"] for row in records}):
        rows = [row for row in records if row["dataset_label"] == source_label]
        is_ood = rows[0]["case_type"] == "out_of_scope"
        accepted_rows = [row for row in rows if row[system]["accepted"]]
        per_category[source_label] = {
            "n": len(rows), "accepted": len(accepted_rows), "rejected": len(rows) - len(accepted_rows),
            "top1_correct": None if is_ood else sum(correct(row) for row in rows),
            "top3_correct": None if is_ood else sum(correct(row, 3) for row in rows),
            "correct_and_accepted": None if is_ood else sum(correct(row) for row in accepted_rows),
        }
    ood_groups = {}
    for group in sorted({row["ood_group"] for row in ood}):
        rows = [row for row in ood if row["ood_group"] == group]
        count = sum(row[system]["accepted"] for row in rows)
        ood_groups[group] = {"n": len(rows), "false_accepts": count,
                             "false_accept_rate": _rate(count, len(rows))}
    return {
        "total_images": len(records), "supported_images": len(supported),
        "mapped_non_ramen_images": len(mapped), "ramen_family_images": len(ramen),
        "out_of_scope_images": len(ood),
        "scope_top1_correct": sum(correct(row) for row in supported),
        "scope_top1_accuracy": _rate(sum(correct(row) for row in supported), len(supported)),
        "scope_top3_correct": sum(correct(row, 3) for row in supported),
        "scope_top3_accuracy": _rate(sum(correct(row, 3) for row in supported), len(supported)),
        "mapped_non_ramen_top1_accuracy": _rate(sum(correct(row) for row in mapped), len(mapped)),
        "mapped_non_ramen_top3_accuracy": _rate(sum(correct(row, 3) for row in mapped), len(mapped)),
        "ramen_family_top1_accuracy": _rate(sum(correct(row) for row in ramen), len(ramen)),
        "ramen_family_top3_accuracy": _rate(sum(correct(row, 3) for row in ramen), len(ramen)),
        "supported_accepts": len(supported_accepted),
        "supported_rejections": len(supported) - len(supported_accepted),
        "supported_acceptance_rate": _rate(len(supported_accepted), len(supported)),
        "scope_rejection_rate": _rate(len(supported) - len(supported_accepted), len(supported)),
        "correct_and_accepted": correct_accepted,
        "correct_and_accepted_rate": _rate(correct_accepted, len(supported)),
        "accepted_in_scope_accuracy": _rate(correct_accepted, len(supported_accepted)),
        "all_accepts": len(accepted),
        "accepted_supported_precision": _rate(correct_accepted, len(accepted)),
        "ood_false_accepts": ood_accepted, "ood_false_accept_rate": _rate(ood_accepted, len(ood)),
        "ood_groups": ood_groups, "per_category": per_category,
        "all_cases_decision_accuracy": _rate(correct_accepted + len(ood) - ood_accepted, len(records)),
    }


def run_comparison(model, processor, out_dir="choob_clip_comparison", batch_size=16,
                   result_path=None):
    """Calibrate once, freeze, then evaluate all 340 predeclared holdout photos.

    The output directory retains a sampling plan, complete image manifest,
    frozen calibration record and final JSON. Reusing completed output is
    rejected so an accidental rerun cannot silently overwrite the holdout.
    """
    from recognition import DishRecognizer

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    destination = Path(result_path) if result_path else out / "clip_comparison.json"
    if destination.exists():
        raise FileExistsError("Completed comparison already exists; preserve its frozen holdout result")
    samples = _download_samples(out)
    calibration = [(image, row) for image, row in samples if row["partition"] == "calibration"]
    holdout = [(image, row) for image, row in samples if row["partition"] == "holdout"]
    if len(calibration) != 260 or len(holdout) != 340:
        raise RuntimeError("Unexpected calibration / holdout counts")
    model.eval()
    recognizer = DishRecognizer(model, processor)
    def score_partition(partition_samples):
        started = time.perf_counter()
        image_features = recognizer.encode_images([image for image, _ in partition_samples],
                                                 batch_size=batch_size)
        elapsed = time.perf_counter() - started
        baseline = recognizer.baseline_scores(image_features)
        optimized = recognizer.score_features(image_features)
        if len(baseline) != len(partition_samples) or len(optimized) != len(partition_samples):
            raise RuntimeError("Model output count differs from the fixed sample count")
        records = []
        for (_, source), original, improved in zip(partition_samples, baseline, optimized):
            original = {
                **original, "accepted": True, "status": "supported",
                "dish_name": original["top_3"][0]["dish_name"],
                "rejection_policy": "none_original_forced_choice",
            }
            records.append({**source, "baseline": original, "optimized_scores": improved})
        return records, elapsed

    calibration_records, calibration_encoding_seconds = score_partition(calibration)
    threshold, selection = _select_threshold(calibration_records)
    recognizer.threshold = threshold
    for row in calibration_records:
        row["optimized"] = {**row["optimized_scores"],
                            **recognizer.predict_from_scores(row["optimized_scores"], threshold=threshold)}
    frozen = {
        "frozen_utc": _utc_now(), "selection": selection,
        "calibration_baseline": _evaluate_records(calibration_records, "baseline"),
        "calibration_optimized": _evaluate_records(calibration_records, "optimized"),
        "calibration_records": calibration_records,
        "holdout_prediction_started": False,
    }
    _write_json(out / "frozen_calibration.json", frozen)
    print("CALIBRATION_FROZEN", json.dumps(selection), flush=True)
    holdout_started_utc = _utc_now()
    holdout_records, holdout_encoding_seconds = score_partition(holdout)
    for row in holdout_records:
        row["optimized"] = {**row["optimized_scores"],
                            **recognizer.predict_from_scores(row["optimized_scores"], threshold=threshold)}
    records = calibration_records + holdout_records
    recognition_file = Path(__import__("recognition").__file__)
    summary = {
        "created_utc": _utc_now(), "source_url": SOURCE,
        "model": getattr(model.config, "_name_or_path", "openai/clip-vit-base-patch32"),
        "device": str(next(model.parameters()).device),
        "recognition_source_sha256": sha256(recognition_file.read_bytes()).hexdigest(),
        "total_images": len(records), "calibration_images": len(calibration_records),
        "holdout_images": len(holdout_records), "threshold_selection": selection,
        "threshold_frozen_utc": frozen["frozen_utc"], "holdout_started_utc": holdout_started_utc,
        "baseline_candidate_labels": BASELINE_CANDIDATES,
        "calibration": {"baseline": frozen["calibration_baseline"],
                        "optimized": frozen["calibration_optimized"]},
        "holdout": {"baseline": _evaluate_records(holdout_records, "baseline"),
                    "optimized": _evaluate_records(holdout_records, "optimized")},
        "encoding_timing": {
            "batch_size": batch_size, "calibration_total_seconds": calibration_encoding_seconds,
            "holdout_total_seconds": holdout_encoding_seconds,
            "holdout_seconds_per_image": holdout_encoding_seconds / len(holdout_records),
            "definition": "Shared batched image encoding only; not separate baseline/optimized latency, and excludes downloads, text-feature setup, scoring, Flask and browser upload.",
        },
        "sampling": "Fixed within-class offsets 20..39 calibration and 100..119 holdout for nine supported families; offsets 20..29 and 100..109 for eight calibration-seen out-of-scope classes; 100..109 for eight additional holdout out-of-scope classes. Every row label and image hash verified before inference, with no post-prediction substitutions.",
        "limitations": [
            "An application inference optimization; no CLIP weight fine-tuning was performed.",
            "This predeclared Food-101 subset is not a representative real-world accuracy estimate.",
            "Ramen correctness is family-only; the dataset cannot establish tonkotsu versus shoyu subtype accuracy.",
            "Additional holdout OOD classes have no calibration photos, but their class names may be in the predefined background candidates; this is not unseen-label OOD generalization.",
            "All images are food; non-food, mixed-dish and real user uploads remain untested in this comparison.",
            "Food-101 validation is held out from Food-101 training; CLIP pretraining overlap is unknown.",
            "Relative softmax values are not calibrated correctness probabilities.",
            "The original forced-choice baseline accepts every photo; rejection improves safety at the cost of some supported-food coverage.",
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_json(destination, {"summary": summary, "records": records})
    _write_json(out / "summary.json", summary)
    print("COMPARISON_SUMMARY", json.dumps(summary, allow_nan=False), flush=True)
    return summary, records
