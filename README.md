---
title: Choob
emoji: 🍽️
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
---

# Choob — Food Passport

Choob helps you remember a dish you loved and decide what to eat next. Scan a meal photo in Snap, save it to your Passport, or tell Discover what you’re craving. The repository opens on `final`, the version used for the final presentation. The earlier versions are preserved in [rehearsal](https://github.com/YeZiyu17/choob-app/tree/rehearsal) and [archive](https://github.com/YeZiyu17/choob-app/tree/archive).

## Final documentation submission

- [English technical report](docs/Choob_Technical_Report_Final.docx): seven pages including references.
- [Submission verification and resource register](docs/SUBMISSION.md): requirement mapping, tested setup, evidence links and remaining limitations.
- [Final Snap regression](evaluation/results/final_snap_2026_11_24/README.md): 40/60 single-dish Top 1; 55/60 target-in-Top-3. The 72 images are a known regression set.
- [Fresh Discover evaluation](evaluation/results/final_discover_2026_11_24/README.md): 12/12 requests returned cards; AI-assisted source audit passed 20/25 cards. This is not a human usability study.
- [Clean-environment setup checks](evaluation/results/submission_check_2026_11_24/README.md): independent dependency installation and application smoke checks, with public model-cache reuse.

## Quick start for final

1. Install **Python 3.12**. The recorded setup verification used macOS ARM64 and Python 3.12.14; Windows commands below are provided but were not tested in that run. On this GitHub page, choose **Code → Download ZIP**, extract the ZIP, and open a terminal in the folder containing `start_choob.py` and `requirements.txt`.
2. Create and activate a virtual environment using the commands for your computer.

   **macOS (Terminal)**

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows (Command Prompt)**

   ```bat
   py -3.12 -m venv .venv
   .venv\Scripts\activate.bat
   ```

3. Install with `python -m pip install -r requirements.txt`. For the exact tested **macOS ARM64 / Python 3.12** dependency set, use `python -m pip install -r requirements-macos-arm64-py312-verified.txt` instead. Run `python -m pip check` to check dependency consistency.
4. Choose how to start Choob in that same terminal.

   | What you want to try | Command |
   | --- | --- |
   | Snap, Passport and the preset Discover choices for Philadelphia | `python start_choob.py --local` (no API keys needed) |
   | The live Discover demo using current restaurant menus | `python start_choob.py` (enter your own Gemini and Tavily API keys when prompted) |

5. Keep the terminal open and visit **[Choob on your computer](http://127.0.0.1:7861/)**. To stop the app, press `Ctrl+C` in the terminal.

**Try your first meal.** In Snap, choose `examples/snap/pizza.jpg` from the extracted folder and select **Scan dish**. Keep the internet connection on: the first scan may download the public model, and later model loading may resolve provider metadata. The recorded clean-environment check reused existing public assets; it did not test a first download. Review the suggested name, choose **Log as eaten**, and open Passport to see the entry. In online Discover, select a city and area and try “I’d like spicy Chinese food.” Open a result’s menu link to check the suggestion.

[Detailed setup and API key links](TEAM_GUIDE.md#run-the-final-build) · [More sample photos](examples/snap/README.md)

## UI flow

The bottom navigation links to **Home, Snap, Passport, Discover, and Connect**. **Passport** shows meals logged in Snap. **Saved dishes** is a separate list available from Discover and Connect. Both persist in the same browser. Fast UI contract checks live in `tests/test_ui_contract.py`. Use the [sample photos and final checklist](TEAM_GUIDE.md#final-checklist) to try the full flow.

## What is actually live?

- **Snap**: Upload one food image to get dish suggestions. **CLIP ViT-B/32** checks the full photo and crops of separate areas for distinct dish families. Review and edit the suggested dishes before logging the meal. The existing nine-family vocabulary includes generic ramen. If recognition is uncertain, enter a dish manually. Relative scores compare model labels and are not calibrated probabilities.
- **Discover**: Choose a cuisine and flavor or type what you’re craving. Local mode uses Qwen and an export of **5,993 restaurant–dish pairs from 3,526 sampled reviews across 123 Philadelphia restaurants**. In Gemini + Tavily mode, Gemini understands the chat input and recommends dishes based on public menus Tavily finds. Each result links to its source. The original `/api/recommend` endpoint still ranks the local embeddings with MiniLM and smoothed review sentiment.
- **Passport**: Shows meals logged in Snap and map stamps for meals with a location. Browser storage retains the meal history on the same device.
- **Connect**: Compares distinct dish types in your Passport stamps with three demo passports. Open a match to add a dish to **Saved dishes**.
- The notebook's GPU-intensive **Qwen2.5-VL-3B** is **not integrated**. Snap uses CLIP with application inference improvements; its weights have not been fine-tuned. Scope checking is a best-effort comparison against a fixed background vocabulary, not reliable identification of every food or non-food object.

### Mobile and Home Screen testing

After installing the dependencies, run `python start_choob.py --lan --port 7873`
and open `http://<computer-Wi-Fi-IP>:7873/` on a phone on the same Wi-Fi. On
macOS, **Start Mobile Online.command** provides the same Gemini + Tavily startup
with hidden key prompts; run `chmod +x "Start Mobile Online.command"` once after
downloading before double-clicking it. The computer must keep running the service.

The PWA adds app icons, installation guidance, standalone display metadata,
phone/landscape layout, and a reconnect page. The service worker caches only
that reconnect page, so teammates' updated UI and AI outputs are not replayed
from an old app cache. Full PWA/service-worker verification needs HTTPS on a
phone; LAN HTTP supports browser testing and any Home Screen entry the browser
offers. See [Mobile setup and test results](MOBILE_TESTING.md) for instructions,
test scope, and Home Screen steps. GitHub stores the code; it does not host the
Flask AI service.

### Try Discover with online menus

The local mode keeps the conversation on your machine and uses the bundled Philadelphia reviews. Quick choices work without a chat model. Free text uses the cached MLX Qwen model in the sibling `recommendation-work` folder. `CHOOB_MLX_PYTHON` and `CHOOB_CHAT_MODEL_PATH` can point to a different local environment and model directory.

**Gemini Flash-Lite + Tavily:** Create a key in [Google AI Studio](https://aistudio.google.com/app/apikey) and [Tavily](https://app.tavily.com/home). Run `python start_choob.py` and paste your keys at the hidden prompts. The launcher also reads `GEMINI_API_KEY` and `TAVILY_API_KEY` from the environment when already set.

Open [the local preview](http://127.0.0.1:7861). Port 7861 lets you try the new mode alongside a running demo on 7860 and has its own browser storage. To use your existing Passport and Saved dishes, restart on port 7860 and open the same address as before. The keys stay in the server environment. Tavily searches menus in the selected city, and Gemini interprets the request and selects dishes supported by those menus. Each batch shows up to three restaurants with a reason and a source. **Show more dishes** looks for additional restaurants with the same preferences. `CHOOB_DISCOVER_CITY` sets the initial city (Philadelphia by default), and `CHOOB_GEMINI_MODEL` can override the default model.

For free online menu search, run the local server with Firecrawl. It accepts keyless requests with a daily limit per IP address. The app sends a menu query built from the selected city and dining preferences, and the local Qwen model selects dishes from the returned menu text. You can use `CHOOB_DISCOVER_CITY` to change the city from Philadelphia. [Firecrawl limits](https://docs.firecrawl.dev/rate-limits)

```bash
CHOOB_DISCOVER_PROVIDER=firecrawl python -m flask --app app run --host 127.0.0.1 --port 7860
```

For OpenAI search, set `OPENAI_API_KEY` in your local server shell and restart with:

```bash
CHOOB_DISCOVER_PROVIDER=openai python -m flask --app app run --host 127.0.0.1 --port 7860
```

Online Discover sends dining preferences to the OpenAI Responses API and uses web search for menu sources. You can set `CHOOB_DISCOVER_CITY` to change the search city from Philadelphia. Keep the key in the server environment. The browser receives cards and links to the menu sources.

### Try the Food Passport map

In Snap, analyze a photo or enter the dish name manually. You can add more dishes and save them as one meal. A meal location and photo are optional. In Passport, open a stamp to see the meal and all its dishes. From **Saved dishes**, tap **I tried this** to prefill the meal. The saved idea is removed when you successfully press **Log as eaten**. Tap **Cancel** to keep it in the list.

The local map uses OpenStreetMap by default and needs an internet connection for the map tiles. To use Google Maps instead, start Flask with a website-restricted Maps JavaScript browser key in `CHOOB_GOOGLE_MAPS_BROWSER_KEY` and an optional `CHOOB_GOOGLE_MAPS_MAP_ID` (defaults to `DEMO_MAP_ID` for testing). Configure the key for the exact local origin you open.

Keep `recognition.py`, `food_vocabulary.py`, and `recognition_config.json` with `app.py`. The original nine-family acceptance threshold remains tied to its frozen vocabulary fingerprint. The broader vocabulary contains 387 candidate labels and aliases for editable suggestions; it is explicitly provisional and is not covered by the old calibration. Changing either vocabulary invalidates the configuration fingerprint instead of silently reusing a threshold. Text prototypes are batched once and cached under the platform cache directory; set `CHOOB_TEXT_CACHE` to choose another location.

The older `requirements-intel-py311.txt` is retained for earlier Intel Mac / Python 3.11 environments. It was not validated in the final setup audit; the tested submission route is the macOS ARM64 / Python 3.12 profile above. Windows, Intel Mac and Docker should be checked separately before relying on those platforms.

## Recognition evaluation

The original 50-photo baseline remains in `evaluation/results/README.md`. The single-dish comparison uses 600 distinct Food-101 validation photos: 260 calibration photos followed by a frozen 340-photo holdout. Previous first-five-per-class photos are excluded. Threshold selection uses only calibration data. Ramen is scored only at family level. That result applies only to the frozen nine-family gate. The 387-label broad suggestion layer and crop-based multi-dish suggestions are experimental, require user confirmation, and have not been calibrated by this comparison. Candidate-label coverage must not be reported as recognition accuracy.

See `evaluation/results/optimization_report.md` and `evaluation/results/clip_comparison.json` for results, individual predictions, limitations and sampling details. These are fixed dataset subsets; do not present them as overall real-world accuracy.

`Choob_Recognition_Optimized.ipynb` preserves the historical October 23 nine-family experiment. It is not a reproduction of the final 387-label or multi-dish application. Its embedded historical implementation and runner must be used together; do not substitute the current recognizer when reproducing that frozen experiment.

For the final application's 72-image regression, use [run_final_snap.py and its instructions](evaluation/results/final_snap_2026_11_24/README.md). For a fresh live Discover campaign, use [run_final_discover.py and the 12-query protocol](evaluation/results/final_discover_2026_11_24/README.md). These evaluation runners require a Git checkout, their documented assets, and a new output directory. A ZIP download is sufficient to run the application itself.

Regression checks use synthetic fixtures and do not download weights:

```bash
python -m unittest discover -s tests -v
```

## Recommendation data and rebuild

The current data is already included in `data/`. Keep the CSV, NPY and JSON manifest together; the backend checks hashes and matrix shape, and loads the embedding model revision recorded in the manifest. See `data/README.md` for the input contract and rebuild commands.

The bundled dish records use **Codex-assisted annotations with exact source quotations**, followed by validation and a separate AI spot check. Qwen experiment outputs are not used in the bundled export. MiniLM embedding and preference inference are actually executed locally; no model weights are fine-tuned. The notebook and `build_recommendations.py` validate a complete supplied annotation file and source-hashed provenance. Original review text, user IDs and annotation checkpoints stay outside the public application package. See `data/DATA_NOTES.md` for the source, sampling and cleaning details.

`evaluation/results/recommendation_smoke.json` records actual MiniLM + Flask test-client inference for five different preferences, an embedding alignment spot check, and malformed/unsupported-request checks. It measures integration, not recommendation accuracy. The separate comparison uses 15 fixed preferences against the saved v1 baseline, and exports a blank human review sheet for Person 5. See `evaluation/results/recommendation_report.md` for details and remaining evaluation work.

## Collaboration

Pull the latest **`final`**, create a feature branch for your change, and open a pull request with **base `final`**. Review and merge one shared-page change at a time, then pull `final` before starting the next change. See the [team workflow](TEAM_GUIDE.md#collaborate-on-the-code). The final branch includes the rehearsal baseline and Mobile work; teammates' subsequent features arrive when their PRs are merged.

## Deployment

This is **Flask + HTML, not a Streamlit app**. Streamlit Community Cloud is not the correct deployment target for this Flask project. An ordinary Python app host (e.g. Render), or a Docker-enabled host (e.g. Hugging Face Spaces Docker) can serve both HTML and endpoints through one URL.

**Shared hosted URL: pending deployment and verification.**

The bundled `Dockerfile` listens on `$PORT` (default 7860), installs CPU PyTorch and runs as user ID 1000. During image construction, `cache_models.py` downloads CLIP and the exact MiniLM revision recorded in the recommendation manifest into a cache owned by the runtime user. The runtime may contact Hugging Face for model metadata or additional public assets; keep network access available. The initial image build needs internet access and may take several minutes; builds fail if required weights cannot be downloaded. No model weights are committed to GitHub.

Build and run locally with Docker:

```bash
docker build -t choob-app .
# Local preset choices, Snap and Passport; no MLX free-text worker is bundled.
docker run --rm -p 7860:7860 choob-app

# Live menus: first set your own keys in the host shell; pass their variable names.
docker run --rm -p 7860:7860 -e CHOOB_DISCOVER_PROVIDER=gemini_tavily -e GEMINI_API_KEY -e TAVILY_API_KEY choob-app
```

For Hugging Face Spaces, use a **Docker** Space and include the README metadata, Dockerfile and all three recommendation export files in `data/`. Check current account eligibility and memory limits with the host before deployment. [Spaces documentation](https://huggingface.co/docs/hub/spaces-overview).

Hosting services vary in RAM, disk and CPU limits. Verify memory capacity, cold starts and both AI endpoints on the selected host. A GPU is not required for the documented CPU route. The final setup audit did not build Docker or verify a hosted deployment. [Render compute plans](https://render.com/docs/compute-plans).

## Further validation

- Upload **two or more new, unseen photos**, not just the embedded example image.
- Test recognition across multiple categories, noting label limitations.
- Try several different text preferences and show the recommendations change with the input.
- Verify Snap → Passport and Discover/Connect → Saved dishes, including phone use.
- Record real accuracy/relevance/latency numbers and compare to a baseline.
- Clearly label sample data vs live inference. Rehearse a backup demo recording.

## Repository map

```
app.py              Flask backend: /api/recognize, /api/recommend
start_choob.py      Launch the final build with Gemini + Tavily; --lan for phone tests
Start Mobile Online.command  macOS Wi-Fi launcher with hidden API key prompts
MOBILE_TESTING.md   Mobile setup, Home Screen instructions and test evidence
static/mobile.*    Isolated phone layout and installation enhancements
static/manifest.webmanifest  App name, icons and standalone launch metadata
build_recommendations.py  Validated extraction, aggregation and aligned export
Choob_Recommendation_Pipeline.ipynb  Self-contained Colab rebuild entry point
recognition.py      CLIP prompt ensembles and scope decision
food_vocabulary.py  Structured provisional food candidates and aliases
multi_dish.py       Suggest distinct dishes from regions of a meal photo
recognition_config.json  Frozen legacy calibration plus provisional broad policy
index.html          Original Choob UI (updated, no frameworks required)
evaluation/         Reproducible comparisons and recorded results
tests/              Recognition and recommendation regression checks
data/               Recommendation CSV, embeddings, manifest and input contract
requirements.txt    Cross-platform dependency ranges
requirements-macos-arm64-py312-verified.txt  Tested platform-specific dependency lock
docs/SUBMISSION.md  Submission scope, evidence and resource references
requirements-intel-py311.txt  Intel Mac / Python 3.11 / PyTorch 2.2.2 profile
Dockerfile          Deployment option
cache_models.py     Cache public model weights during Docker image construction
.dockerignore       Keep private inputs, local caches and environments out of images
.gitignore          Avoid accidental uploads
```
