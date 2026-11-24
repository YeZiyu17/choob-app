"""Replay frozen Discover queries against an explicitly started online service.

By default this prints the plan and makes no HTTP/API requests. Use --run to
collect a NEW evaluation; it cannot reconstruct the presentation's old figures.
Menu-card verification is deliberately left to a separate reviewer worksheet.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener


HERE = Path(__file__).resolve().parent
DEFAULT_PROTOCOL = HERE / "final_discover_protocol.json"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    # Every run owns a new directory. Refuse to replace an existing artifact.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def load_protocol(path):
    raw = path.read_bytes()
    protocol = json.loads(raw)
    cases = protocol["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("The protocol must contain at least one case.")
    ids = [case["id"] for case in cases]
    if len(set(ids)) != len(ids) or any(
        not isinstance(value, str) or not value.isalnum() for value in ids
    ):
        raise ValueError("Case IDs must be unique alphanumeric strings.")
    for case in cases:
        request = case["request"]
        if not isinstance(request, dict) or not isinstance(request.get("city"), str):
            raise ValueError("Every case needs a request object and city.")
        if not isinstance(request.get("message"), str) or not request["message"].strip():
            raise ValueError("Every case needs a nonempty message.")
    return protocol, hashlib.sha256(raw).hexdigest()


def request_json(base_url, endpoint, payload=None, timeout=300):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(base_url + endpoint, data=data,
                      headers={"Content-Type": "application/json"})
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        try:
            response = json.load(error)
        except (ValueError, OSError):
            response = {"error": "Non-JSON HTTP error response."}
        return error.code, response
    except (URLError, TimeoutError, OSError, ValueError) as error:
        return None, {"error": "Client transport/response error: " + str(error)}


def request_outcome(record):
    status = record["status"]
    response = record["response"]
    results = response.get("results", []) if isinstance(response, dict) else []
    if status == 200:
        return "returned_recommendations" if results else "empty_without_http_error"
    error = response.get("error", "") if isinstance(response, dict) else ""
    if status == 503 and "Gemini is temporarily busy" in error:
        return "gemini_busy_http_503"
    if status == 503 and "Gemini" in error and (
        "too long" in error or "timed out" in error
    ):
        return "gemini_timeout_http_503"
    return "client_transport_error" if status is None else "other_http_error"


def summarize_requests(records):
    outcomes = {}
    for record in records:
        label = request_outcome(record)
        outcomes[label] = outcomes.get(label, 0) + 1
    count = len(records)
    successful = outcomes.get("returned_recommendations", 0)
    errors = sum(record["status"] != 200 for record in records)
    return {
        "requests": count,
        "requests_returning_recommendations": successful,
        "request_success_rate": successful / count if count else None,
        "empty_without_http_error": outcomes.get("empty_without_http_error", 0),
        "errors": errors,
        "outcomes": outcomes,
        "returned_cards": sum(len(record["response"].get("results", []))
                              for record in records
                              if isinstance(record["response"], dict)),
        "card_audit_status": "pending_separate_manual_source_review",
        "verified_cards": None,
        "verified_card_rate": None,
        "definitions": {
            "request_success": "HTTP 200 with at least one returned recommendation card.",
            "busy": "HTTP 503 and the explicit Gemini temporarily-busy error message.",
            "timeout": "HTTP 503 and an explicit Gemini timeout message; separate from busy.",
            "card_quality": "Never inferred from request success or the app's own evidence checks.",
        },
    }


def write_blank_audit(path, records):
    fields = ["request_id", "rank", "city", "requested_cuisine", "requested_taste",
              "requested_region", "requested_dish", "dish", "restaurant", "source_url",
              "menu_item", "current_venue_city", "cuisine", "flavor",
              "region_or_named_dish", "verdict_pass_fail_insufficient", "evidence",
              "verification_urls", "reviewed_utc", "reviewer"]
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in records:
            expected = record.get("expected", {})
            response = record["response"]
            cards = response.get("results", []) if isinstance(response, dict) else []
            for rank, card in enumerate(cards, 1):
                writer.writerow({
                    "request_id": record["id"], "rank": rank,
                    "city": record["request"]["city"],
                    "requested_cuisine": expected.get("cuisine", ""),
                    "requested_taste": expected.get("taste", ""),
                    "requested_region": expected.get("region", ""),
                    "requested_dish": expected.get("dish", ""),
                    "dish": card.get("dish_name", ""),
                    "restaurant": card.get("restaurant_name", ""),
                    "source_url": card.get("source_url", ""),
                })


def local_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE.parent,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--base-url", default="http://127.0.0.1:7873")
    parser.add_argument("--output", type=Path, help="New output directory; must not already exist.")
    parser.add_argument("--run", action="store_true", help="Explicitly enable live HTTP/API requests.")
    parser.add_argument("--server-commit", help="Verified serving commit, recorded as operator-declared.")
    parser.add_argument("--model", help="Server Gemini model, recorded as operator-declared.")
    parser.add_argument("--timeout", type=float, default=300, help="Per-request client timeout in seconds.")
    args = parser.parse_args()
    protocol, protocol_hash = load_protocol(args.protocol)
    if not args.run:
        print(json.dumps({"mode": "plan_only_no_network_no_files_written",
                          "protocol": protocol, "protocol_sha256": protocol_hash,
                          "next_step": "Start the online service, then use --run --output NEW_DIRECTORY "
                                       "--server-commit VERIFIED_COMMIT --model ACTUAL_MODEL."},
                         ensure_ascii=False, indent=2))
        return 0
    if args.output is None or not args.server_commit or not args.model:
        parser.error("--run requires --output, --server-commit and --model.")
    base_url = args.base_url.rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        parser.error("--base-url must be an HTTP(S) service URL without credentials.")
    if args.timeout <= 0:
        parser.error("--timeout must be positive.")
    if args.output.exists():
        parser.error("The output directory already exists; choose a new one to preserve evidence.")
    status, config = request_json(base_url, "/api/discover/config", timeout=10)
    if status != 200 or not isinstance(config, dict) or (
        config.get("provider") != "gemini_tavily" or not config.get("online_ready")
    ):
        parser.error("The service is not configured for online Gemini + Tavily; no query was sent.")
    safe_config = {key: config[key] for key in
                   ("provider", "city", "online_ready", "cities", "neighborhoods") if key in config}
    if any(case["request"]["city"] not in config.get("cities", []) for case in protocol["cases"]):
        parser.error("The protocol contains a city not supported by this service.")
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {
        "started_utc": utc_now(), "base_url": base_url, "protocol_sha256": protocol_hash,
        "runner_repository_commit": local_commit(),
        "operator_declared_server_commit": args.server_commit,
        "operator_declared_gemini_model": args.model,
        "server_config": safe_config, "concurrency": 1,
        "client_timeout_seconds": args.timeout,
        "client_retries": 0,
        "server_internal_retries": "Included in each request; log server retry/model information separately.",
        "purpose": "New final-build rerun; not a reconstruction of historical presentation percentages.",
    }
    save_json(args.output / "protocol.json", {"run": metadata, "frozen_protocol": protocol})
    records = []
    try:
        for case in protocol["cases"]:
            started = time.monotonic()
            requested_utc = utc_now()
            status, response = request_json(base_url, "/api/discover/chat", case["request"], args.timeout)
            record = {**case, "requested_utc": requested_utc, "status": status,
                      "seconds": round(time.monotonic() - started, 4), "response": response}
            records.append(record)
            save_json(args.output / ("request_" + case["id"] + ".json"), record)
            print(case["id"], status, request_outcome(record), flush=True)
    finally:
        save_json(args.output / "requests.json", {"run": metadata, "results": records})
        summary = {"completed_utc": utc_now(), "planned_requests": len(protocol["cases"]),
                   "campaign_complete": len(records) == len(protocol["cases"]),
                   **summarize_requests(records)}
        save_json(args.output / "summary.json", summary)
        write_blank_audit(args.output / "card_audit_blank.csv", records)
    print("Request logs saved. Menu verification remains blank and requires separate source review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
