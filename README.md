---
title: Choob
emoji: 🍽️
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
---

# Choob — Shared Working AI Prototype

For instructors and evaluators, start with the [rehearsal setup guide](TEAM_GUIDE.md#run-the-rehearsal-build). This branch contains the rehearsal version. Download it and run the app on your own computer; the GitHub page displays the code and documentation rather than a running application.

This project preserves the group's **original Choob HTML UI**, adds real food-photo upload and a dynamically populated Discover panel, and supplies Python endpoints for recognition and recommendations. The current recognition reproduction notebook is [Choob_Recognition_Optimized.ipynb](Choob_Recognition_Optimized.ipynb).

## UI flow

The bottom navigation links to **Home, Snap, Passport, Discover, and Connect**. **Passport** shows meals logged in Snap. **Saved dishes** is a separate list available from Discover and Connect. Both persist in the same browser. Fast UI contract checks live in `tests/test_ui_contract.py`. Use the [sample photos and rehearsal checklist](TEAM_GUIDE.md#rehearsal-checklist) to try the full flow.

## What is actually live?

- **Snap**: Upload one food image to get dish suggestions. **CLIP ViT-B/32** checks the full photo and crops of separate areas for distinct dish families. Review and edit the suggested dishes before logging the meal. The existing nine-family vocabulary includes generic ramen. If recognition is uncertain, enter a dish manually. Relative scores compare model labels and are not calibrated probabilities.
- **Discover**: Choose a cuisine and flavor or type what you’re craving. Local mode uses Qwen and an export of **5,993 restaurant–dish pairs from 3,526 sampled reviews across 123 Philadelphia restaurants**. In Gemini + Tavily mode, Gemini understands the chat input and recommends dishes based on public menus Tavily finds. Each result links to its source. The original `/api/recommend` endpoint still ranks the local embeddings with MiniLM and smoothed review sentiment.
- **Passport**: Shows meals logged in Snap and map stamps for meals with a location. Browser storage retains the meal history on the same device.
- **Connect**: Compares distinct dish types in your Passport stamps with three demo passports. Open a match to add a dish to **Saved dishes**.
- **Evaluation**: Open **View model evaluation report** from Snap to see recorded recognition tests and build metadata for the local recommendation data.
- The notebook's GPU-intensive **Qwen2.5-VL-3B** is **not integrated**. Snap uses CLIP with application inference improvements; its weights have not been fine-tuned. Scope checking is a best-effort comparison against a fixed background vocabulary, not reliable identification of every food or non-food object.

## Quick start for rehearsal

### 1. Download and install

Open the [choob-rehearsal branch](https://github.com/YeZiyu17/choob-app/tree/choob-rehearsal), choose **Code > Download ZIP**, and extract the ZIP. Install **Python 3.11**, then open a terminal in the extracted folder containing `app.py` and `requirements.txt`. A GitHub account is not required to download this public repository.

On macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, use **Command Prompt (CMD)**; select **Add Python to PATH** when installing Python:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

**Intel Mac:** Replace the installation command above with `python -m pip install -r requirements-intel-py311.txt` in the activated Python 3.11 environment. This profile uses PyTorch 2.2.2 and NumPy below 2.

### 2. Choose how to run Discover

**Online menus and free-text requests:** Obtain your own [Gemini](https://aistudio.google.com/app/apikey) and [Tavily](https://app.tavily.com/home) API keys, then run:

```bash
python start_choob.py
```

Paste both keys at the hidden terminal prompts. The cursor may appear not to move while you type. Keys already set in the server environment are reused; keys are not included in the repository. Online Discover needs internet access and valid access to both services.

**Without API keys:** Run:

```bash
python start_choob.py --local
```

Use the cuisine and flavor choice buttons in Discover to explore the bundled Philadelphia data. Local free-text chat requires a separate MLX/Qwen environment and model that are not bundled here. Without that extra setup, the app offers the choice buttons instead. Local mode still needs internet on a fresh installation to download dependencies and model weights; the first image scan downloads CLIP, and the first local recommendations may download MiniLM. Map tiles also need internet access.

### 3. Open and test the app

Open **http://127.0.0.1:7861/** on the computer running the server. Keep the terminal open; press `Ctrl+C` there to stop the app. This local address does not let someone on another computer open your server. For later runs, activate `.venv` again and run the same launch command.

Start with a [sample food photo](examples/snap/README.md) in Snap, review the suggestions, log a meal, and inspect Passport. Then try Discover and Connect using the [rehearsal checklist](TEAM_GUIDE.md#rehearsal-checklist). Meals and saved dishes persist in the same browser at the same address and port.

If port 7861 is busy, use `python start_choob.py --port 7863` (or add `--local` for local mode), then open **http://127.0.0.1:7863/**. See the [detailed setup and troubleshooting guide](TEAM_GUIDE.md#run-the-rehearsal-build) if startup fails.

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

On an Intel Mac with Python 3.11 and PyTorch 2.2.2, install `requirements-intel-py311.txt`. It keeps NumPy below 2 for compatibility and does not add another recognition provider or require credentials.

## Recognition evaluation

The original 50-photo baseline remains in `evaluation/results/README.md`. The single-dish comparison uses 600 distinct Food-101 validation photos: 260 calibration photos followed by a frozen 340-photo holdout. Previous first-five-per-class photos are excluded. Threshold selection uses only calibration data. Ramen is scored only at family level. That result applies only to the frozen nine-family gate. The 387-label broad suggestion layer and crop-based multi-dish suggestions are experimental, require user confirmation, and have not been calibrated by this comparison. Candidate-label coverage must not be reported as recognition accuracy.

See `evaluation/results/optimization_report.md` and `evaluation/results/clip_comparison.json` for results, individual predictions, limitations and sampling details. These are fixed dataset subsets; do not present them as overall real-world accuracy.

`Choob_Recognition_Optimized.ipynb` is a clean Colab entry point containing the same recognizer and comparison runner. Use a fresh CPU runtime and run its cells in order. Its opening summary records the completed run; code outputs are deliberately empty until it is executed again.

To reproduce in Colab with `recognition.py` in the current directory and the original `model` / `processor` loaded:

```python
exec(open("evaluation/run_clip_comparison.py").read())
summary, records = run_comparison(model, processor)
```

Use a fresh output directory for an intentional new experiment. A completed comparison is protected against accidental overwrite. Source photos are downloaded to that runtime and are not bundled with this project.

Regression checks use synthetic fixtures and do not download weights:

```bash
python -m unittest discover -s tests -v
```

## Recommendation data and rebuild

The current data is already included in `data/`. Keep the CSV, NPY and JSON manifest together; the backend checks hashes and matrix shape, and loads the embedding model revision recorded in the manifest. See `data/README.md` for the input contract and rebuild commands.

The bundled dish records use **Codex-assisted annotations with exact source quotations**, followed by validation and a separate AI spot check. Qwen experiment outputs are not used in the bundled export. MiniLM embedding and preference inference are actually executed locally; no model weights are fine-tuned. The notebook and `build_recommendations.py` validate a complete supplied annotation file and source-hashed provenance. Original review text, user IDs and annotation checkpoints stay outside the public application package. See `data/DATA_NOTES.md` for the source, sampling and cleaning details.

`evaluation/results/recommendation_smoke.json` records actual MiniLM + Flask test-client inference for five different preferences, an embedding alignment spot check, and malformed/unsupported-request checks. It measures integration, not recommendation accuracy. The separate comparison uses 15 fixed preferences against the saved v1 baseline, and exports a blank human review sheet for Person 5. See `evaluation/results/recommendation_report.md` for details and remaining evaluation work.

## Collaboration

For rehearsal, create a branch from `choob-rehearsal` and open a pull request back into `choob-rehearsal`. See the [team workflow](TEAM_GUIDE.md#collaborate-on-the-code) for review and integration steps.

## Deployment

This is **Flask + HTML, not a Streamlit app**. Streamlit Community Cloud is not the correct deployment target for this Flask project. An ordinary Python app host (e.g. Render), or a Docker-enabled host (e.g. Hugging Face Spaces Docker) can serve both HTML and endpoints through one URL.

**Shared hosted URL: pending deployment and verification.**

The bundled `Dockerfile` listens on `$PORT` (default 7860), installs CPU PyTorch and runs as user ID 1000. During image construction, `cache_models.py` downloads CLIP and the exact MiniLM revision recorded in the recommendation manifest into a cache owned by the runtime user. The container then uses those cached weights offline. The initial image build needs internet access and may take several minutes; builds fail if required weights cannot be downloaded. No model weights are committed to GitHub.

Build and run locally with Docker:

```bash
docker build -t choob-app .
docker run --rm -p 7860:7860 choob-app
```

For Hugging Face Spaces, create a **Docker** Space and copy the application files, including this README's metadata, the Dockerfile and all three recommendation export files in `data/`. Current HF rules require paid-plan eligibility for a new Docker Space even when selecting CPU Basic; check the account before creation. [Official Spaces hardware rules](https://huggingface.co/docs/hub/spaces-gpus).

Hosting services vary in RAM, disk and CPU limits. Render's Free service has only 512 MB RAM, which is insufficient for the full PyTorch + CLIP + MiniLM application; use a host with enough memory and verify both AI endpoints after deployment. CPU hosting may experience slow cold starts. A GPU is not required. [Render compute plans](https://render.com/docs/compute-plans).

## Before the intermediate project demo

- Upload **two or more new, unseen photos**, not just the embedded example image.
- Test recognition across multiple categories, noting label limitations.
- Try several different text preferences and show the recommendations change with the input.
- Verify the entire Snap/Discover → Collect flow.
- Record real accuracy/relevance/latency numbers and compare to a baseline.
- Clearly label sample data vs live inference. Rehearse a backup demo recording.

## Repository map

```
app.py              Flask backend: /api/recognize, /api/recommend
start_choob.py      Launch the rehearsal build with Gemini + Tavily
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
requirements.txt    Python dependencies
requirements-intel-py311.txt  Intel Mac / Python 3.11 / PyTorch 2.2.2 profile
Dockerfile          Deployment option
cache_models.py     Cache public model weights during Docker image construction
.dockerignore       Keep private inputs, local caches and environments out of images
.gitignore          Avoid accidental uploads
```
