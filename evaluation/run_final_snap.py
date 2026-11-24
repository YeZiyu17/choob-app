"""Re-evaluate the submitted Snap endpoint on the frozen rehearsal photographs.

This is a same-image final-build regression evaluation, not a new holdout.
Images and model weights stay outside the repository. See --help for inputs.
Only the CLIP asset resolver is replaced; /api/recognize and the recognizer run
unchanged. Primary predictions and ranked alternatives are scored separately.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter
from urllib.parse import unquote, urlsplit


REPOSITORY = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path(__file__).with_name("final_snap_cases_2026_11_24.json")
ALIASES = {
    "hamburger": ["cheeseburger", "smash burger", "burger"],
    "french fries": ["fries"],
    "fried eggs": ["fried egg", "sunny side up eggs"],
    "scrambled eggs": ["scrambled egg"],
    "sushi": ["nigiri", "nigiri sushi", "maki", "sushi roll", "sushi rolls"],
    "chicken wings": ["buffalo wings", "fried chicken wings"],
    "cheesecake": ["new york cheesecake", "basque cheesecake"],
    "pancakes": ["pancake", "buttermilk pancakes", "blueberry pancakes"],
    "waffles": ["waffle", "belgian waffles"],
}
RUNTIME_FILES = [
    "app.py", "recognition.py", "recognition_config.json", "food_vocabulary.py",
    "multi_dish.py", "discover_ai.py", "discover_chat.py", "discover_firecrawl.py",
    "discover_gemini.py", "discover_online.py", "discover_areas.py",
    "discover_tastes.py", "discover_tavily.py",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def normalized(value):
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def canonical(value):
    value = normalized(value)
    return next((key for key, aliases in ALIASES.items() if value in aliases), value)


def compare(expected, predicted, normalize):
    left, right = set(map(normalize, expected)), set(map(normalize, predicted))
    return {
        "correct": sorted(left & right), "missed": sorted(left - right),
        "extra_relative_to_scored_targets": sorted(right - left),
        "exact_set_match": left == right, "all_targets_found": left <= right,
        "expected_count": len(left), "predicted_count": len(right),
    }


def git(*args):
    return subprocess.check_output(["git", *args], cwd=REPOSITORY, text=True).strip()


def verify_runtime(expected_commit):
    commit = git("rev-parse", "HEAD")
    if expected_commit and commit != expected_commit:
        raise ValueError(f"Expected commit {expected_commit}, found {commit}")
    hashes = {}
    for name in RUNTIME_FILES:
        actual = (REPOSITORY / name).read_bytes()
        committed = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPOSITORY)
        if actual != committed:
            raise ValueError(f"Runtime source differs from the recorded commit: {name}")
        hashes[name] = sha256(actual).hexdigest()
    return commit, hashes


def roots_from_args(values):
    roots = {}
    for value in values:
        name, sep, directory = value.partition("=")
        if not sep or not name or not directory or name in roots:
            raise ValueError("Use distinct --case-root ROUND=/path/to/original/round arguments")
        roots[name] = Path(directory).expanduser().resolve()
    return roots


def image_path(case, args, roots):
    relative = Path(case["file"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Manifest image paths must be relative and remain inside the image root")
    if case["round"] in roots:
        return roots[case["round"]] / relative
    if args.images_root:
        return args.images_root / case["round"] / relative
    raise ValueError(f"No image directory for {case['round']}; provide --case-root or --images-root")


def download_image(case, path):
    """Resolve canonical sources; accept downloaded bytes only at the frozen hash.

    Commons files were EXIF-oriented, RGB-converted, uniformly resized to at
    most 1100px and saved as JPEG quality 92 in the original evaluation. JPEG
    encoders can differ; a hash mismatch stops the evaluation instead of
    silently replacing the frozen photograph with a changed input.
    """
    import requests
    from PIL import Image, ImageOps

    headers = {"User-Agent": "ChoobAcademicEvaluation/1.0 (https://github.com/YeZiyu17/choob-app)"}
    def get(url, **kwargs):
        response = requests.get(url, headers=headers, timeout=30, **kwargs)
        response.raise_for_status()
        return response
    if case["group"] == "food101_expanded":
        response = get("https://datasets-server.huggingface.co/rows", params={
            "dataset": "ethz/food101", "config": "default", "split": "validation",
            "offset": case["row_idx"], "length": 1,
        }).json()
        entry = response["rows"][0]
        names = next(item["type"]["names"] for item in response["features"] if item["name"] == "label")
        if entry["row_idx"] != case["row_idx"] or names[entry["row"]["label"]] != case["dataset_label"]:
            raise ValueError(f"Dataset row or reference label changed: {case['id']}")
        payload = get(entry["row"]["image"]["src"]).content
    else:
        title = unquote(urlsplit(case["source"]).path).split("/wiki/", 1)[1]
        metadata = get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "format": "json", "formatversion": "2",
            "titles": title, "prop": "imageinfo", "iiprop": "url",
        }).json()
        source_url = metadata["query"]["pages"][0]["imageinfo"][0]["url"]
        raw = get(source_url.partition("?")[0]).content
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        image.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=92)
        payload = output.getvalue()
    if sha256(payload).hexdigest() != case["sha256"]:
        raise ValueError(f"Downloaded input differs from the frozen image: {case['id']}; supply the original cached file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def preflight(args):
    manifest_raw = args.manifest.read_bytes()
    manifest = json.loads(manifest_raw)
    cases = manifest["cases"]
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("A nonempty manifest with unique case IDs is required")
    roots = roots_from_args(args.case_root)
    inputs = []
    for case in cases:
        if not case.get("expected") or not re.fullmatch(r"[a-f0-9]{64}", case.get("sha256", "")):
            raise ValueError(f"Missing frozen targets/hash: {case['id']}")
        path = image_path(case, args, roots)
        if not path.is_file() and args.download_images:
            download_image(case, path)
        if not path.is_file():
            raise FileNotFoundError(f"Image missing: {path}")
        payload = path.read_bytes()
        if sha256(payload).hexdigest() != case["sha256"]:
            raise ValueError(f"Image hash mismatch: {case['id']}")
        inputs.append((case, path))
    if len({case["sha256"] for case in cases}) != len(cases):
        raise ValueError("The fixed evaluation must not contain duplicate image bytes")
    commit, source_hashes = verify_runtime(args.expected_commit)
    if args.assets:
        for name in ("config.json", "preprocessor_config.json", "tokenizer.json", "model.safetensors"):
            if not (args.assets / name).is_file():
                raise FileNotFoundError(f"Missing model asset: {name}")
    return manifest, sha256(manifest_raw).hexdigest(), inputs, commit, source_hashes


def average(rows, key):
    values = [row[key] for row in rows]
    return sum(values) / len(values) if values else None


def rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def summarize(rows):
    single = [row for row in rows if row["case"]["group"] == "food101_expanded"]
    mixed = [row for row in rows if row["case"]["group"] == "commons_multi_real"]
    result = {"cases": len(rows), "http_status_counts": dict(Counter(str(row["http_status"]) for row in rows))}
    for mode in ("strict", "alias_aware"):
        single_correct = sum(row["single_scores"][mode]["top1_correct"] for row in single)
        single_top3 = sum(row["single_scores"][mode]["top3_contains_target"] for row in single)
        expected = sum(row["primary_scores"][mode]["expected_count"] for row in mixed)
        found = sum(len(row["primary_scores"][mode]["correct"]) for row in mixed)
        extras = sum(len(row["primary_scores"][mode]["extra_relative_to_scored_targets"]) for row in mixed)
        result[mode] = {
            "single_main_result_top1": rate(single_correct, len(single)),
            "single_main_result_top3": rate(single_top3, len(single)),
            "single_output_exact_target_set": rate(sum(row["primary_scores"][mode]["exact_set_match"] for row in single), len(single)),
            "mixed_primary_target_recall": rate(found, expected),
            "mixed_photos_all_targets_found": rate(sum(row["primary_scores"][mode]["all_targets_found"] for row in mixed), len(mixed)),
            "mixed_photos_exact_target_set": rate(sum(row["primary_scores"][mode]["exact_set_match"] for row in mixed), len(mixed)),
            "mixed_extra_suggestions_relative_to_scored_targets": extras,
            "mixed_photos_with_extra_suggestions": sum(bool(row["primary_scores"][mode]["extra_relative_to_scored_targets"]) for row in mixed),
        }
    durations = [row["endpoint_seconds"] for row in rows]
    result["descriptive_endpoint_timing"] = {
        "n": len(durations), "first_request_seconds": durations[0],
        "mean_seconds": statistics.mean(durations), "median_seconds": statistics.median(durations),
        "min_seconds": min(durations), "max_seconds": max(durations),
        "definition": "Sequential Flask test-client wall time; first request includes recognizer/text-cache setup. Excludes model loading, networking, browser upload/rendering and production concurrency. Descriptive only.",
    }
    result["per_round"] = {}
    for round_name in sorted({row["case"]["round"] for row in rows}):
        group = [row for row in rows if row["case"]["round"] == round_name]
        result["per_round"][round_name] = {
            "cases": len(group),
            "single_top1_strict": sum(row["single_scores"].get("strict", {}).get("top1_correct", False) for row in group),
            "single_top3_strict": sum(row["single_scores"].get("strict", {}).get("top3_contains_target", False) for row in group),
            "mixed_targets_found_strict": sum(len(row["primary_scores"]["strict"]["correct"]) for row in group if row["case"]["group"] == "commons_multi_real"),
        }
    return result


def run(args):
    manifest, manifest_hash, inputs, commit, source_hashes = preflight(args)
    print(f"PREFLIGHT_OK {len(inputs)} distinct images; commit {commit}", flush=True)
    if args.validate_only:
        return
    if not args.output:
        raise ValueError("--output is required for an inference run")
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Use a new output directory; previous results/protocol are never overwritten")
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.allow_model_download:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    # Runtime text features are regenerated, not bundled with public results.
    os.environ["CHOOB_TEXT_CACHE"] = tempfile.mkdtemp(prefix="choob-final-snap-text-")
    sys.path.insert(0, str(REPOSITORY))
    protocol = {
        "frozen_before_inference_utc": now(), "executed_local_commit": commit,
        "runtime_source_sha256": source_hashes, "runner_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "manifest_sha256": manifest_hash, "case_count": len(inputs), "cases": manifest["cases"],
        "design": manifest["design"], "predeclared_aliases": ALIASES,
        "scoring": {
            "single_top1": "The main API response dish_name equals its single reference after normalization; do not credit arbitrary regional alternatives as first-choice identification.",
            "single_top3": "The reference appears in main-response ranked_guesses[:3]; these are alternatives to one identification, not three separate dishes.",
            "primary_set": "Set of primary dish_name values in response dishes; matched, missed and extra scored independently.",
            "mixed_recall": "Matched primary targets / all predeclared target dishes; all-target-photo rate is separate.",
            "extras": "Suggestions outside the scored target set; some visible accompaniments were explicitly unscored, so these counts are not full ground-truth precision.",
            "normalization": "Lowercase alphanumeric word tokens with whitespace collapse; alias-aware results use only the frozen aliases above.",
            "errors": "HTTP failures count as empty predictions; never remove failed cases from denominators.",
        },
        "execution": "Unchanged Flask /api/recognize with locally supplied official CLIP assets. Only get_clip asset resolution is replaced; model and processor remain pretrained and inference rules are unmodified.",
        "limitations": [
            "Previously evaluated fixed photographs; a same-image regression rerun, not new independent or unseen test data.",
            "Top-three candidate coverage is not automatic first-choice identification accuracy.",
            "No user-selection success, browser interaction, production latency or overall real-world food accuracy is established.",
            "The two original rounds have separate source images, with 60 single-dish and 12 mixed-meal photos in total.",
        ],
    }
    write_json(args.output / "protocol.json", protocol)
    import torch
    from transformers import CLIPModel, CLIPProcessor
    import app as choob

    torch.set_num_threads(args.threads)
    model_source = args.assets or "openai/clip-vit-base-patch32"
    started = perf_counter()
    model = CLIPModel.from_pretrained(model_source, local_files_only=not args.allow_model_download,
                                    use_safetensors=True, low_cpu_mem_usage=False, device_map=None).cpu().eval()
    processor = CLIPProcessor.from_pretrained(model_source, local_files_only=not args.allow_model_download)
    model_load_seconds = perf_counter() - started
    choob.get_clip = lambda: (model, processor)
    choob.app.logger.disabled = True
    environment = {
        "python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
        "cpu_threads": args.threads, "torch_device": "cpu", "model_load_seconds": model_load_seconds,
        "packages": {name: importlib.metadata.version(name) for name in
                     ["torch", "transformers", "flask", "pillow", "numpy", "pandas", "requests", "sentence-transformers"]},
        "model_id": "openai/clip-vit-base-patch32", "model_config_sha256": sha256((args.assets / "config.json").read_bytes()).hexdigest() if args.assets else None,
        "model_weights_sha256": sha256((args.assets / "model.safetensors").read_bytes()).hexdigest() if args.assets else None,
        "environment_note": "Record actual installed versions. This is not a fresh requirements installation; Pillow 13.0.0 exceeds the repository's declared pillow<13 range when present.",
    }
    write_json(args.output / "environment.json", environment)
    print(f"MODEL_READY load_seconds={model_load_seconds:.3f}", flush=True)
    client, rows = choob.app.test_client(), []
    for index, (case, path) in enumerate(inputs, 1):
        started = perf_counter()
        response = client.post("/api/recognize", data={"image": (io.BytesIO(path.read_bytes()), path.name)}, content_type="multipart/form-data")
        duration = perf_counter() - started
        body = response.get_json() or {}
        successful = response.status_code == 200
        primary = [item["dish_name"] for item in body.get("dishes", []) if isinstance(item.get("dish_name"), str)] if successful else []
        whole_top1 = body.get("dish_name", "") if successful else ""
        whole_top3 = [item["dish_name"] for item in body.get("ranked_guesses", [])[:3]] if successful else []
        row = {
            "case": case, "http_status": response.status_code, "endpoint_seconds": duration,
            "main_result_top1": whole_top1, "main_result_top3": whole_top3,
            "primary_dishes": primary, "primary_scores": {}, "single_scores": {}, "api_response": body,
        }
        for mode, normalize in [("strict", normalized), ("alias_aware", canonical)]:
            row["primary_scores"][mode] = compare(case["expected"], primary, normalize)
            if case["group"] == "food101_expanded":
                target = normalize(case["expected"][0])
                row["single_scores"][mode] = {
                    "top1_correct": successful and normalize(whole_top1) == target,
                    "top3_contains_target": successful and target in set(map(normalize, whole_top3)),
                }
        rows.append(row)
        write_json(args.output / "predictions.json", {"created_utc": now(), "commit": commit, "manifest_sha256": manifest_hash, "cases": rows})
        print(f"{index:02}/{len(inputs)} {case['id']} expected={case['expected']} primary={primary} top3={whole_top3} http={response.status_code} seconds={duration:.3f}", flush=True)
    summary = summarize(rows)
    summary.update(created_utc=now(), executed_local_commit=commit, manifest_sha256=manifest_hash)
    write_json(args.output / "summary.json", summary)
    import csv
    with (args.output / "predictions.csv").open("w", newline="", encoding="utf-8") as output:
        fields = ["id", "round", "group", "expected", "primary", "whole_top1", "whole_top3", "single_top1_strict", "single_top3_strict", "matched_targets", "missed_targets", "extra_relative_to_scored_targets", "http_status", "endpoint_seconds", "source", "sha256"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            case = row["case"]
            writer.writerow({
                **{key: case[key] for key in ["id", "round", "group", "source", "sha256"]},
                "expected": " | ".join(case["expected"]), "primary": " | ".join(row["primary_dishes"]),
                "whole_top1": row["main_result_top1"], "whole_top3": " | ".join(row["main_result_top3"]),
                "single_top1_strict": row["single_scores"].get("strict", {}).get("top1_correct", ""),
                "single_top3_strict": row["single_scores"].get("strict", {}).get("top3_contains_target", ""),
                "matched_targets": " | ".join(row["primary_scores"]["strict"]["correct"]),
                "missed_targets": " | ".join(row["primary_scores"]["strict"]["missed"]),
                "extra_relative_to_scored_targets": " | ".join(row["primary_scores"]["strict"]["extra_relative_to_scored_targets"]),
                "http_status": row["http_status"], "endpoint_seconds": row["endpoint_seconds"],
            })
    print("FINAL_SUMMARY " + json.dumps(summary, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--images-root", type=Path, help="Root containing round1/snap_images and round2/snap_images")
    parser.add_argument("--case-root", action="append", default=[], help="ROUND=/path/to/original/round; can be repeated")
    parser.add_argument("--assets", type=Path, help="Local official CLIP model.safetensors/config/processor directory")
    parser.add_argument("--allow-model-download", action="store_true", help="Allow pretrained model resolution to access the network")
    parser.add_argument("--download-images", action="store_true", help="Resolve missing images from canonical sources, then require the frozen SHA256")
    parser.add_argument("--expected-commit", help="Require this exact checked-out commit")
    parser.add_argument("--output", type=Path, help="New, empty results directory")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--validate-only", action="store_true", help="Verify all images/assets/runtime sources without model loading or inference")
    args = parser.parse_args()
    if not 1 <= args.threads <= 64:
        parser.error("--threads must be between 1 and 64")
    try:
        run(args)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Evaluation stopped: {error}\n")


if __name__ == "__main__":
    main()
