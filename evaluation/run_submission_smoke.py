"""Check real app dependencies/routes; allow public model access, block external inference APIs."""
from __future__ import annotations

import argparse
import hashlib
import os
import site
import importlib.metadata
import io
import json
import pathlib
import platform
import sys
import threading
import time
import traceback
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", required=True, type=pathlib.Path)
parser.add_argument("--app-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
parser.add_argument("--model-cache", type=pathlib.Path, default=pathlib.Path.home()/".cache/huggingface/hub")
args = parser.parse_args()
ROOT = args.output_dir.resolve()
SOURCE = args.app_dir.resolve()
ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SOURCE))
sys.dont_write_bytecode = True
# Mask known provider keys without reading or printing their inherited values.
for variable in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "TAVILY_API_KEY", "OPENAI_API_KEY", "FIRECRAWL_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
    os.environ[variable] = ""
os.environ.update(HF_HOME=str(ROOT/"hf-home"), HF_HUB_CACHE=str(args.model_cache.resolve()),
                  HF_HUB_DISABLE_IMPLICIT_TOKEN="1", HF_HUB_DISABLE_XET="1",
                  HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1", CHOOB_TEXT_CACHE=str(ROOT/"text-cache"),
                  CHOOB_DISCOVER_PROVIDER="local", CHOOB_DISCOVER_CITY="Philadelphia")
os.environ["HF_TOKEN_PATH"] = str(ROOT/"hf-home/no-token")
os.environ["CHOOB_GOOGLE_MAPS_BROWSER_KEY"] = ""
for variable in ("CHOOB_CLIP_MODEL_PATH", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
    os.environ.pop(variable, None)
venv_cfg = pathlib.Path(sys.prefix)/"pyvenv.cfg"
venv_settings = {line.partition("=")[0].strip(): line.partition("=")[2].strip() for line in venv_cfg.read_text().splitlines() if "=" in line} if venv_cfg.exists() else {}
system_packages = venv_settings.get("include-system-site-packages", "").lower() == "true"
isolation = {"is_venv": sys.prefix != sys.base_prefix, "include_system_site_packages": system_packages,
             "user_site_enabled": site.ENABLE_USER_SITE,
             "pass": sys.prefix != sys.base_prefix and venv_cfg.exists() and not system_packages and not site.ENABLE_USER_SITE}
report = {
    "audit_date": "2026-11-24",
    "source": str(SOURCE),
    "baseline_commit_before_submission_check": "4ebda3596cc6898f698912df553d87346e9fe5d2",
    "app_sha256": hashlib.sha256((SOURCE/"app.py").read_bytes()).hexdigest(),
    "source_sha256": {name: hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
                      for name in ("app.py", "cache_models.py", "recognition.py", "multi_dish.py", "food_vocabulary.py", "recognition_config.json")},
    "python": sys.version,
    "platform": platform.platform(),
    "environment_isolation": isolation,
    "first_model_download_test": False,
    "model_cache_reused": str(args.model_cache.resolve()),
    "model_access": "Public Hugging Face model metadata and file access allowed; existing cache reused.",
    "online_discover_requests": 0,
    "public_model_requests": [],
    "blocked_external_request_attempts": [],
    "checks": [],
    "limits": [
        "Verified macOS ARM64 Python 3.12 only; Python 3.11 and Intel/Windows profiles were not tested.",
        "Public pre-trained model cache is reused; first model download is not tested.",
        "No online Discover inference or real keys are used.",
        "Backend integration checks do not establish browser, phone, or UX behavior.",
        "Bundled Snap photos are illustrative smoke tests, not independent accuracy data.",
        "Public Hugging Face metadata/file requests are allowed and recorded; other external requests are blocked.",
    ],
}


def record(name, response, expected, request=None):
    body = response.get_json(silent=True)
    item = {"name": name, "status": response.status_code, "expected_status": expected,
            "pass": response.status_code == expected}
    if request is not None:
        item["request"] = request
    if body is not None:
        item["response"] = body
    else:
        item["content_type"] = response.content_type
        item["body_bytes"] = len(response.data)
    report["checks"].append(item)
    print(name, response.status_code, "PASS" if item["pass"] else "FAIL", flush=True)
    return body


try:
    import requests

    original_send = requests.sessions.Session.send

    def guarded_send(self, prepared, **kwargs):
        from urllib.parse import urlsplit
        parsed = urlsplit(prepared.url)
        host, path, method = parsed.hostname or "", parsed.path, prepared.method.upper()
        safe_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        model_prefixes = ("/api/models/openai/clip-vit-base-patch32", "/api/models/sentence-transformers/all-MiniLM-L6-v2",
                          "/openai/clip-vit-base-patch32/", "/sentence-transformers/all-MiniLM-L6-v2/",
                          "/api/resolve-cache/models/openai/clip-vit-base-patch32/",
                          "/api/resolve-cache/models/sentence-transformers/all-MiniLM-L6-v2/")
        public_hub = parsed.scheme == "https" and host == "huggingface.co" and path.startswith(model_prefixes)
        public_cdn = parsed.scheme == "https" and host in {"cdn-lfs.huggingface.co", "cdn-lfs-us-1.hf.co", "cdn-lfs-eu-1.hf.co", "cas-bridge.xethub.hf.co"}
        local = host in {"localhost", "127.0.0.1", "::1"}
        if method not in {"GET", "HEAD"} or not (local or public_hub or public_cdn):
            report["blocked_external_request_attempts"].append({"method": method, "url": safe_url})
            raise RuntimeError("Only public model metadata/files and loopback HTTP are allowed")
        event = {"method": method, "url": safe_url}
        if not local:
            report["public_model_requests"].append(event)
        try:
            result = original_send(self, prepared, **kwargs)
            event["status"] = result.status_code
            return result
        except Exception as exc:
            event["error_type"] = type(exc).__name__
            raise

    # Guard send, rather than request, so Requests redirects are checked too.
    requests.sessions.Session.send = guarded_send
    import app as backend
    from PIL import Image
    from werkzeug.serving import make_server

    report["import"] = "pass"
    report["routes"] = sorted(str(rule) for rule in backend.app.url_map.iter_rules())
    report["installed_versions"] = {
        name: importlib.metadata.version(name) for name in (
            "flask", "gunicorn", "numpy", "pandas", "pillow", "torch",
            "transformers", "sentence-transformers", "requests", "huggingface-hub",
        )
    }
    client = backend.app.test_client()
    for route in ("/", "/api/status", "/api/recommendation-summary", "/service-worker.js",
                  "/offline.html", "/static/manifest.webmanifest", "/api/passport-map-config"):
        record("GET " + route, client.get(route), 200)

    # Real loopback HTTP server startup, independent of the already running demo.
    try:
        server = make_server("127.0.0.1", 0, backend.app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/status", timeout=10) as resp:
            report["http_startup"] = {"pass": resp.status == 200, "status": resp.status,
                                      "response": json.loads(resp.read())}
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
    except (Exception, SystemExit):
        report["http_startup"] = {"pass": False, "error": traceback.format_exc()}

    record("Snap missing upload", client.post("/api/recognize"), 400)
    for label, raw in (("empty", b""), ("corrupt", b"not an image")):
        record("Snap " + label, client.post("/api/recognize", data={"image": (io.BytesIO(raw), "test.jpg")}), 400)
    big = io.BytesIO()
    Image.new("RGB", (4001, 4000), "orange").save(big, format="PNG")
    record("Snap pixel limit", client.post("/api/recognize", data={"image": (io.BytesIO(big.getvalue()), "huge.png")}), 400)
    record("Snap byte limit", client.post("/api/recognize", data={"image": (io.BytesIO(b"x"*(8*1024*1024+1)), "large.jpg")}), 413)

    backend.app.config["DISCOVER_PROVIDER"] = "gemini_tavily"
    settings = record("Discover Gemini config without keys", client.get("/api/discover/config"), 200)
    report["discover_no_keys_ready_false"] = settings.get("online_ready") is False
    malformed = [None, [], {}, {"message": ""}, {"message": 1}, {"message": "x"*401},
                 {"message": "Japanese", "preferences": []},
                 {"message": "Japanese", "city": "Not a city"},
                 {"message": "Japanese", "neighborhood": "Not a neighborhood"},
                 {"message": "Japanese", "partner": []}]
    for i, payload in enumerate(malformed):
        response = client.post("/api/discover/chat", data="null", content_type="application/json") if payload is None else client.post("/api/discover/chat", json=payload)
        record(f"Discover invalid schema {i+1}", response, 400, payload)
    record("Discover unsupported dietary request", client.post("/api/discover/chat", json={"message":"peanut allergy"}), 422)
    record("Discover Gemini request without keys", client.post("/api/discover/chat", json={"message":"Japanese"}), 503)
    backend.app.config["DISCOVER_PROVIDER"] = "openai"
    record("Discover OpenAI request without key", client.post("/api/discover/chat", json={"message":"Japanese"}), 503)
    backend.app.config["DISCOVER_PROVIDER"] = "local"
    first = record("Discover local cuisine turn", client.post("/api/discover/chat", json={"message":"Japanese"}), 200)
    record("Discover local taste turn", client.post("/api/discover/chat", json={"message":"Spicy", "preferences":first["preferences"]}), 200)
    # Real local CLIP inference; public model access is allowed, paid APIs are blocked.
    for name in ("pizza", "sushi", "hamburger"):
        path = SOURCE / "examples" / "snap" / (name + ".jpg")
        raw = path.read_bytes()
        started = time.monotonic()
        body = record("Snap real cached CLIP " + name, client.post("/api/recognize", data={"image":(io.BytesIO(raw),path.name)}), 200)
        aliases = {"pizza": ("pizza",), "sushi": ("sushi",), "hamburger": ("hamburger", "burger", "cheeseburger")}[name]
        returned = [row.get("dish_name", "") for row in body.get("dishes", [])] if isinstance(body, dict) else []
        expected_observed = any(alias in label.casefold() for label in returned for alias in aliases)
        report["checks"][-1].update(image_sha256=hashlib.sha256(raw).hexdigest(), elapsed_seconds=round(time.monotonic()-started, 3),
                                     expected_label=name, returned_labels=returned, expected_label_observed=expected_observed)
        report["checks"][-1]["pass"] = report["checks"][-1]["pass"] and expected_observed
    report["cache_info"] = str(backend.get_clip.cache_info())
except Exception:
    report["fatal_error"] = traceback.format_exc()
    print(report["fatal_error"], flush=True)
finally:
    report["pass_count"] = sum(c["pass"] for c in report["checks"])
    report["check_count"] = len(report["checks"])
    report["all_passed"] = bool(isolation["pass"] and report.get("import") == "pass" and report.get("http_startup", {}).get("pass") and report["pass_count"] == report["check_count"] and not report.get("fatal_error"))
    (ROOT / "submission_smoke.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("Saved", ROOT / "submission_smoke.json", "all_passed=", report["all_passed"], flush=True)

raise SystemExit(0 if report["all_passed"] else 1)
