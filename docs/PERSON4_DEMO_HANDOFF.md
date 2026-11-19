# Person 4 — November 2 Intermediate Demo Handoff

## Current delivery decision

The current delivery target is a reproducibly installable and stable local Flask application. No account system, database, community backend, framework migration, or paid deployment was added for the demo. The implementation preserves Person 1's single-page UI and directly uses Person 3's CLIP recognition, MiniLM recommendation logic, CSV/NPY/manifest artifacts, and existing evaluation records.

The original Project Forward Guidelines and the instructor's latest email attachments or full text are not present in the repository. This document follows the summary supplied by the team. The final submission must still follow the official Brightspace instructions.

## Architecture and data flow

```text
index.html (Person 1 UI)
  ├─ Snap upload ──> Flask /api/recognize ──> CLIP ViT-B/32
  │                                        └─ Prompt ensemble + recorded scope threshold
  ├─ Discover text ─> Flask /api/recommend ─> all-MiniLM-L6-v2
  │                                          ├─ Data CSV + 5,993×384 NPY
  │                                          ├─ Manifest hash/version validation
  │                                          └─ 85% similarity + 15% dish sentiment
  ├─ Results ─────> /api/recommendation-summary ─> Current manifest build metadata
  └─ Collect ─────> Browser localStorage ─> Refresh persistence + dish/restaurant deduplication
```

Image recognition and text recommendation are separate systems. CLIP ranks nine supported dish families and uses scope checking to decide whether to return Unknown. MiniLM encodes a preference and compares it with Yelp-derived dish-description vectors. They are not the same model.

The application uses a historical Yelp-derived sample: 3,526 reviews, 123 Philadelphia restaurants, 8,667 evidence-backed review–dish mentions, and 5,993 restaurant–dish pairs. The team implemented data validation and manifests, scope checking, the ranking formula, Flask APIs, UI flows, and tests. Neither CLIP nor MiniLM was fine-tuned. The Qwen2.5-VL-3B model from the notebook is not integrated into the application.

## Verification completed on November 1, 2026

### Automated and simulated checks

- Existing Intel environment: 61/61 passed.
- Independently created clean Intel environment: 61/61 passed.
- These checks use synthetic fixtures and mocks to validate APIs, error handling, ranking arithmetic, data consistency, and cache refresh behavior. They are not model-accuracy results.
- Added coverage includes Flask serving the original UI and status API, empty/corrupt/over-8-MB images, valid images reaching the recognizer, and model failure returning 503.

### Real model calls

- MiniLM: loaded the manifest-pinned revision and validated the 5,993-row × 384-dimensional CSV/NPY export and hashes. Three preferences produced Sushi, Tiramisu Dessert, and Spicy Fish as their top semantic matches, demonstrating that the output changes with the input.
- CLIP: ran three sequential predictions on each of two newly selected external photos.
  - [Pizza.jpeg](https://commons.wikimedia.org/wiki/File:Pizza.jpeg), SHA-256 `a5c3fe114e310199c76b59336b451de2a9ba6f8c23d37744cbde0c357cda9819`: returned Pizza with `accepted=true`.
  - [Sushi!.jpg](https://commons.wikimedia.org/wiki/File:Sushi!.jpg), SHA-256 `1c83bce3be348d73d9e6bf6687fbbc197087c5fd4de9b3493deeb992fd3f93aa`: returned Unknown with Sushi as the suggested candidate and `accepted=false`; the manual-entry flow worked.
- These photos were not in the repository's recorded evaluation files and were selected for this Person 4 verification. Two results must not be presented as an accuracy estimate.

### Real HTTP checks

- Home page, `/api/status`, and `/api/recommendation-summary`: HTTP 200.
- Three different preferences: three different Top-5 lists, all HTTP 200.
- Real inference on both photos: HTTP 200.
- Empty preference: 400; unverified gluten-free request: 422; missing image: 400; corrupt image: 400; upload larger than 8 MB: 413.
- Cold HTTP requests, including loading, inference, Flask, and loopback networking: approximately 8.57 seconds for MiniLM and 20.63 seconds for CLIP.
- Warm HTTP requests: approximately 0.033 and 0.024 seconds for two MiniLM requests, and approximately 0.690 seconds for the second CLIP photo.

### Browser checks

The following flows were observed in a real browser: Snap confirmation and manual correction, two different Discover preferences, source labels on saved items, refresh persistence, duplicate handling, latest-request-wins behavior, and current Results build metadata. See `evaluation/results/person4_browser_verification_2026-11-01.md`.

### Clean Intel environment

- `x86_64`, macOS 26.7.1, Python 3.11.9.
- Installed `requirements-intel-mac.txt` in an empty virtual environment; `pip check` passed.
- Home and status endpoints returned 200; 61/61 tests passed; real CLIP and MiniLM inference succeeded.
- The models were already cached, so download time was not measured. The clean process took approximately 80.43 seconds to load the recommendation artifacts and model. The first MiniLM encode took approximately 1.43 seconds, with the next two averaging approximately 0.013 seconds. CLIP model and prompt-cache construction took approximately 4.25 seconds; the first inference took approximately 0.284 seconds, with the next five averaging approximately 0.203 seconds.
- This is one local measurement and must not be generalized to every Intel Mac.

Machine-readable evidence:

- `evaluation/results/person4_clean_intel_benchmark_2026-11-01.json`
- `evaluation/results/person4_intel_benchmark_2026-11-01.json`
- `evaluation/results/person4_http_verification_2026-11-01.json`

## Ten-minute pre-demo checklist

1. Connect the laptop to power and close memory-intensive applications.
2. Run `source .venv/bin/activate`.
3. Run `python -m pip check`.
4. Run `python cache_models.py` while a reliable network is still available.
5. Run `python app.py`.
6. Open `http://127.0.0.1:7860/`.
7. Privately make one Discover request and one Snap request to warm the process.
8. Keep local copies of both demo photos and close unrelated tabs and notifications.

## Recording plan: under five minutes

Target duration: approximately 4:40.

1. **0:00–0:25 — Scope and changes:** Explain that this is a local end-to-end application using the project's own UI, data, and models. A public deployment is not a current demo requirement.
2. **0:25–1:15 — Normal Snap result:** Upload the Pizza photo and click the round analysis button. Identify the result as live CLIP inference and explain that the relative score is not a probability. Confirm Pizza and save it.
3. **1:15–2:00 — Safe Snap fallback:** Upload the Sushi photo. Show Unknown and the Sushi suggested candidate. Enter `Sushi` manually and save it. Explain that the application does not invent cuisine or category metadata after an uncertain result.
4. **2:00–2:25 — Collect:** Show Pizza as `Live Snap inference` and the corrected Sushi item as `Snap · manual dish name`. Refresh to confirm persistence. Save a duplicate and show that the count does not increase.
5. **2:25–3:35 — Discover:** Enter `I want sushi with fresh fish.` and save the first result. Then enter `I want a sweet dessert, such as tiramisu or cheesecake.` and show that the Top-5 list changes. State that the historical Yelp sample cannot verify current menus, allergens, or dietary suitability.
6. **3:35–4:20 — Results:** Show the current 3,526 / 8,667 / 5,993 build counts. Explain that the recognition metrics and saved recommendation example are recorded results, not outputs from the two just-uploaded photos. State that human recommendation-relevance evaluation is still pending from Person 5.
7. **4:20–4:40 — Technical challenge and close:** Briefly explain that `torch>=2.3` could not be installed on the Intel Mac, so a separate `torch 2.2.2` profile was created and both real models were verified in a clean environment. State that the Brightspace AI Trust Lab options are still required before the classroom test can be implemented.

Do not wait for cold loading during the recording. Warm the process first. If cold-start numbers must be shown, display this document or the saved results instead of restarting during the recording.

## Demo fallback plan

- **Models are cached but the network is unavailable:** The loader checks the local cache first. Restart Flask and continue. Do not clear `~/.cache/huggingface`.
- **Cold loading is slow:** Keep the server process running and warm both features before recording.
- **The live network or model fails:** Show the explicit error message and the Results page's `RECORDED` evidence, then play the prepared short backup recording. Do not describe recorded output as live inference.
- **A photo returns Unknown:** This is an expected safety behavior. Demonstrate the confirmation/correction flow. Pizza is the verified accepted demo photo.
- **The port is occupied:** Stop the older process, or run `PORT=7861 python app.py` and open that address.
- **The application cannot start:** Preserve the Git commit, JSON evidence, and backup video. Do not migrate frameworks or purchase deployment resources during the demo window.

## Changes since Showcase

The repository does not identify a Showcase commit or include the Showcase materials, so no arbitrary commit can be treated as the confirmed baseline. The changes below are supported by Git history, but the team must confirm whether every item occurred after Showcase. Commit `7762fc2` from October 19, 2026 is a possible UI baseline, not a confirmed Showcase tag.

- October 23, 2026: added the CLIP prompt ensemble, cached text features, competing background categories, frozen-threshold scope checking, Food-101 calibration/holdout records, and API checks (`d83cc89` through `5b05de1`).
- October 23, 2026: added real Yelp-derived recommendation data, MiniLM inference, the Flask recommendation API, and team setup guidance (`45d89b9` through `38cb3ca`).
- October 29, 2026: expanded recommendation coverage to 123 restaurants, 3,526 reviews, and 5,993 pairs; added the manifest, baseline comparison, Person 5 plan, and current-build Results metadata (`bf6d133` through `b075696`).
- Current Person 4 branch: added the separate Intel Mac dependency profile, cache-first offline startup, Snap/Discover timeouts and request-order protection, collection source labels and deduplication, additional Flask tests, HTTP/browser/clean-environment evidence, and demo documentation.

Before submission, the team should provide the Showcase slide deck or video date and its commit/tag so the baseline can be confirmed and the pending label removed.

## Short Person 4 contribution statement

“Person 4 completed Choob's Flask/UI end-to-end integration and runtime support. The work preserved the original UI and Person 3's models and data; added error handling, request-order protection, and source labeling across Snap, Discover, Collect, and Results; resolved Intel Mac Python 3.11/PyTorch installation compatibility and cache-first offline startup; verified both AI features in a clean environment, through real HTTP, and in a browser; and prepared reusable demo, troubleshooting, and verification materials.”

## Materials still required from other team members

- **Person 3:** Confirm that this branch still matches the final model and data versions. Confirm that no later recognition threshold or model description supersedes the recorded version. Provide only traceable results for any newer model evaluation.
- **Person 5:** Complete the human relevance judgments in `recommendation_human_review.csv` and the associated report. Do not present the 61 interface and integration checks as recommendation accuracy.
- **Team:** Provide the Showcase baseline materials and the exact text of the two Brightspace AI Trust Lab options. Record the chosen test, actual result, and team reflection only after the classroom activity occurs.

## Recommended submission checklist

- Code on an independent branch with a reviewed PR; do not merge directly into `main`.
- `requirements-intel-mac.txt` and `docs/INTEL_MAC_SETUP.md`.
- This handoff document, the Person 4 JSON evidence, and the browser verification record.
- A recording link under five minutes and the necessary backup recording.
- Person 3's model/data version statement and Person 5's completed human evaluation.
- The AI Trust Lab option, actual execution results, and team reflection after the classroom activity.
- Exclude `.venv`, model caches, temporary test photos, private raw data, and secrets.

Final submission contents, deadline, and format must follow the official Brightspace requirements and the instructor's latest email.
