"""Evaluate Choob's existing ten-label CLIP baseline on fixed Food-101 samples.

Uses dataset labels, not model predictions, as ground truth. Images stay local.
Run in Colab with the already loaded model and processor:
    run_evaluation(model, processor)
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import statistics
import time

import requests
import torch
from PIL import Image

API = "https://datasets-server.huggingface.co"
DATASET = "ethz/food101"
SOURCE = "https://huggingface.co/datasets/ethz/food101"
CANDIDATES = [
    "tonkotsu ramen", "shoyu ramen", "sushi", "dumplings", "fried rice",
    "pad thai", "pizza", "pasta", "hamburger", "tacos",
]
# Mapping is fixed before predictions. Food-101 does not label ramen subtypes.
GROUPS = [
    ("dumplings", "dumplings", "in_scope"),
    ("fried_rice", "fried rice", "in_scope"),
    ("hamburger", "hamburger", "in_scope"),
    ("pad_thai", "pad thai", "in_scope"),
    ("pizza", "pizza", "in_scope"),
    ("spaghetti_bolognese", "pasta", "in_scope"),
    ("sushi", "sushi", "in_scope"),
    ("tacos", "tacos", "in_scope"),
    ("ramen", "ramen", "ramen_family_only"),
    ("apple_pie", None, "out_of_scope"),
]


def api_get(endpoint, **extra):
    response = requests.get(
        API + endpoint,
        params={"dataset": DATASET, "config": "default", "split": "validation", **extra},
        timeout=40,
    )
    response.raise_for_status()
    return response.json()


def run_evaluation(model, processor, out_dir="choob_clip_evaluation", per_class=5):
    out = Path(out_dir)
    image_dir = out / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    features = api_get("/first-rows")["features"]
    names = next(f["type"]["names"] for f in features if f["name"] == "label")
    label_ids = {name: index for index, name in enumerate(names)}

    # Food-101 has 250 validation images per class. Discover the class blocks
    # through the rows endpoint; this avoids waiting for the filter index.
    def inspect_block(block):
        data = api_get("/rows", offset=block * 250, length=1)
        entry = data["rows"][0]
        return entry["row"]["label"], entry["row_idx"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        blocks = list(pool.map(inspect_block, range(len(names))))
    offsets = {}
    for label_id, row_idx in blocks:
        offsets.setdefault(label_id, row_idx)
    print("Located", len(offsets), "label blocks.", flush=True)

    def get_group(group):
        source_label, expected, case_type = group
        data = api_get("/rows", offset=offsets[label_ids[source_label]], length=per_class)
        if len(data["rows"]) != per_class:
            raise RuntimeError("Incomplete sample group: " + source_label)
        return [(group, entry) for entry in data["rows"]]

    with ThreadPoolExecutor(max_workers=4) as pool:
        selected = [item for group_rows in pool.map(get_group, GROUPS) for item in group_rows]
    print("Selected", len(selected), "validation photos before inference.", flush=True)

    def download(item):
        group, entry = item
        source_label, expected, case_type = group
        if entry["row"]["label"] != label_ids[source_label]:
            raise ValueError("Dataset filter returned an unexpected label")
        response = requests.get(entry["row"]["image"]["src"], timeout=60)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
        path = image_dir / (source_label + "_" + str(entry["row_idx"]) + ".jpg")
        path.write_bytes(response.content)
        return image, {
            "dataset": DATASET, "split": "validation", "row_idx": entry["row_idx"],
            "dataset_label": source_label, "expected_label": expected, "case_type": case_type,
            "image_file": str(path.relative_to(out)), "image_sha256": sha256(response.content).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        samples = list(pool.map(download, selected))

    model.eval()
    device = next(model.parameters()).device

    def infer(image):
        inputs = processor(text=[f"a photo of {name}" for name in CANDIDATES], images=image, return_tensors="pt", padding=True)
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            scores = model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()
        return sorted(zip(CANDIDATES, scores), key=lambda pair: pair[1], reverse=True)

    # The separate warm-up is excluded from per-image processing times.
    started = time.perf_counter()
    infer(samples[0][0])
    warmup_seconds = time.perf_counter() - started
    records = []
    for image, record in samples:
        started = time.perf_counter()
        ranking = infer(image)
        record["processing_seconds"] = round(time.perf_counter() - started, 6)
        record["top_3"] = [{"dish_name": name, "relative_score": round(score, 7)} for name, score in ranking[:3]]
        predicted = [name for name, _ in ranking[:3]]
        expected = record["expected_label"]
        record["top1_correct"] = predicted[0] == expected if record["case_type"] == "in_scope" else None
        record["top3_correct"] = expected in predicted if record["case_type"] == "in_scope" else None
        record["ramen_family_top1"] = predicted[0] in {"tonkotsu ramen", "shoyu ramen"} if record["case_type"] == "ramen_family_only" else None
        records.append(record)
        print(record["dataset_label"], record["row_idx"], "->", predicted[0], record["processing_seconds"], "s", flush=True)
    scored = [row for row in records if row["case_type"] == "in_scope"]
    per_category = {}
    for source_label, expected, case_type in GROUPS:
        if case_type == "in_scope":
            rows = [row for row in scored if row["dataset_label"] == source_label]
            per_category[source_label] = {"n": len(rows), "top1_correct": sum(row["top1_correct"] for row in rows), "top3_correct": sum(row["top3_correct"] for row in rows)}
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "source_url": SOURCE,
        "model": "openai/clip-vit-base-patch32", "device": str(device), "candidate_labels": CANDIDATES,
        "sampling": f"First {per_class} rows of each predeclared validation class block, discovered at fixed 250-row intervals; labels verified before inference; no selection based on predictions.",
        "total_images": len(records), "in_scope_images": len(scored),
        "top1_correct": sum(row["top1_correct"] for row in scored),
        "top3_correct": sum(row["top3_correct"] for row in scored),
        "top1_accuracy": sum(row["top1_correct"] for row in scored) / len(scored),
        "top3_accuracy": sum(row["top3_correct"] for row in scored) / len(scored),
        "mean_processing_seconds": statistics.mean(row["processing_seconds"] for row in records),
        "median_processing_seconds": statistics.median(row["processing_seconds"] for row in records),
        "warmup_seconds": warmup_seconds, "per_category": per_category,
        "limitations": [
            "Small fixed subset, not a representative benchmark of all categories.",
            "Eight mapped categories only; generic ramen cannot establish subtype accuracy.",
            "Candidate list forces a known label for out-of-scope foods; no rejection mechanism.",
            "Relative softmax scores are not calibrated confidence.",
            "Measures model processing after download and warm-up, not Flask or browser latency.",
            "Food-101 validation is held out from its train split; CLIP pretraining overlap is unknown.",
        ],
    }
    (out / "results.json").write_text(json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("EVALUATION_SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)
    return summary, records
