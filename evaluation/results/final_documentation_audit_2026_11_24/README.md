# Discover evidence audit, November 24, 2026

This folder reconciles the **November 16 historical build `3725948`**, not a new run of the final app. No external requests or new menu reviews were performed.

- Requests returning recommendations: **11/18 (61.1%)**.
- Empty without an HTTP error: **3/18 (16.7%)**.
- Gemini-related HTTP 503 errors: **4/18 (22.2%)**, comprising **3 busy messages** and **1 timeout message**. Strict busy alone is **3/18 (16.7%)**.
- Recorded card audits: **17/26 pass (65.4%)**, **4/26 fail**, **5/26 insufficient evidence**. Insufficient cases remain in the denominator.

`discover_historical_audit.json` contains all 18 original request/response records and all 26 recorded card audits, their original sources and SHA-256 hashes. The summary JSON provides compact counts. These are repeated nine-query rounds in four cities; cards and queries can repeat. Existing audit judgments are retained rather than independently re-reviewed.

The presentation's twelve-request/five-city campaign and its **75% / 76% / 17%** figures lack located raw records and exact denominators. They are excluded from the verified results here. A new final-build run cannot reconstruct those historical figures.

## Optional new evaluation

`evaluation/run_final_discover.py` prints the frozen nine-case plan by default, makes no network requests and writes no files. An explicit `--run` is required. It calls an already-started Gemini + Tavily service and does not read or accept API keys.

```bash
python evaluation/run_final_discover.py
python evaluation/run_final_discover.py --run --base-url http://127.0.0.1:7873 --output evaluation/results/NEW_DISCOVER_RUN --server-commit VERIFIED_SERVING_COMMIT --model ACTUAL_SERVER_MODEL
```

Use a new output directory. The default frozen protocol replays the old nine cases in four cities; it does not invent the missing twelve-case protocol. The runner saves request-level logs and an **unlabeled card audit CSV**. Review every returned card separately against menu item, current venue/city, cuisine and all applicable flavor/region/named-dish constraints. Record evidence URLs, access date, reviewer and pass/fail/insufficient. Successful app responses and the app's source checks are not independent menu verification. Model and serving commit are operator-declared because the existing status/config endpoints do not expose them. The client runs sequentially, whereas the historical script used two workers; do not claim a controlled latency or failure-rate comparison.
