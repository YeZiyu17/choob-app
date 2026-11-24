# Submission installation and backend smoke check — 24 November 2026

The declared `requirements.txt` installed successfully in a new macOS ARM64 Python 3.12.14 virtual environment with no system or user site packages. `pip-check.txt` records no broken requirements. `requirements-macos-arm64-py312-verified.txt` at the repository root pins the 43 resolved packages. Python 3.11, Intel macOS, Windows, Docker builds, first model download, and browser/phone behavior were not tested by this run.

The normal networked application passed **31 of 31 backend checks**, plus a real loopback Flask HTTP startup/status request. The checks cover public pages/status, malformed and oversized photo inputs, Discover malformed requests, unsupported dietary requests, missing Gemini/Tavily and OpenAI keys, two local Discover turns, and three real CLIP image requests. These are integration checks, not a new accuracy study.

Actual example-photo suggestions were:

| Bundled photo | Returned suggestions |
|---|---|
| pizza.jpg | Pizza |
| sushi.jpg | Sushi; Kimbap |
| hamburger.jpg | Hamburger; Kofta; Caesar Salad; Cheese Plate |

The expected category appeared in every response. The extra suggestions show why the UI requires user review; a successful request does not mean every suggestion was correct. Timings describe this one machine/run and include model loading, public metadata lookup and cold text-prototype preparation for the first photo. They are not latency benchmarks.

The app's model-loading and recognition files were unchanged from public `final` commit `4ebda3596cc6898f698912df553d87346e9fe5d2`. Their hashes are recorded in `submission_smoke.json`. Existing public CLIP and MiniLM model caches were reused directly, without an alternate model path or asset overlay. Public Hugging Face metadata and model-file access was enabled: 32 GET/HEAD requests, including optional-file probes and redirects, were recorded. No external inference API requests were made, and no requests were blocked during this successful run. This is a cache-reuse test with normal public model networking, not a first-time model-download test. Cached file hashes are in `model_cache_provenance.json`.

No real API keys were read or used. The runner masks known provider-key variables, disables implicit Hugging Face tokens, and allows only public Hugging Face model GET/HEAD requests and loopback HTTP. Other external Requests traffic, including Gemini and Tavily, is blocked. Online Discover relevance remains covered by the separately archived final campaign; this check did not repeat it. The real Flask app and actual local model code were exercised without inference stubs.

To repeat after installing the declared dependencies:

```bash
python evaluation/run_submission_smoke.py --app-dir . --output-dir /tmp/choob-submission-smoke
```

The runner uses the normal model-loading path and permits public Hugging Face networking. Use `--model-cache /path/to/huggingface/hub` only when selecting another existing public Hub cache. Models, tokens, virtual environments and generated runtime caches should remain outside version control.

The separate full regression suite passed **134 tests**; see `regression-tests.txt`. Mocked error responses in that log are intentional negative tests and do not represent live service requests.
