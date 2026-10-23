---
title: Choob
emoji: 🍽️
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
---

# Choob — Shared Working AI Prototype

组员请先看：[中文协作与本地运行指南](TEAM_GUIDE.md)。目前使用 GitHub 协作，各自在自己的电脑运行 App。

This project preserves the group's **original Choob HTML UI**, adds real food-photo upload and a dynamically populated Discover panel, and supplies Python endpoints based on the same models/logic as `Choob_AI_Dish_Recognition.ipynb`.

## What is actually live?

- **Snap**: Upload a new food image. The original pretrained **CLIP ViT-B/32** weights now use four prompt templates, dish synonyms, cached text features and competing background categories. Nine supported dish families include generic **ramen**; tonkotsu/shoyu subtypes are not asserted. A calibrated scope check can return **Unknown**. The UI requires confirmation or a manually entered dish name and makes clear that relative scores are **not calibrated probabilities**.
- **Discover**: Enter an English dish or taste preference. The server uses **Sentence-Transformers all-MiniLM-L6-v2**, the bundled Yelp-derived records and embeddings, and an 85% similarity + 15% smoothed dish-sentiment formula. The current export contains **711 restaurant–dish pairs from 484 sampled reviews across 50 Philadelphia restaurants**. Common explicit dietary/allergy requests return a clear unsupported-request message; review text cannot verify ingredients or dietary suitability.
- **Collect**: Saved dishes persist locally in the same browser via `localStorage`. There is **no multi-user account storage** yet.
- **Connect**, sample restaurant, sample challenges and results screen: illustrative UI, **not live community data**. The evaluation screen shows previously recorded Colab results, not live test metrics.
- The notebook's GPU-intensive **Qwen2.5-VL-3B** is **not integrated**. Snap uses CLIP with application inference improvements; its weights have not been fine-tuned. Scope checking is a best-effort comparison against a fixed background vocabulary, not reliable identification of every food or non-food object.

## Quick start (local development)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:7860**. First image inference downloads CLIP weights and may take a while. The first recommendation downloads MiniLM weights. Both need internet and enough RAM.

Check connection: http://localhost:7860/api/status

Keep `recognition.py` and `recognition_config.json` with `app.py`. The scope threshold is tied to a fingerprint of the prompt vocabulary. Changing that vocabulary requires recalibration; an absent or stale configuration causes recognition to return a clear backend error instead of silently using an arbitrary threshold.

## Recognition evaluation

The original 50-photo baseline remains in `evaluation/results/README.md`. The new comparison uses 600 distinct Food-101 validation photos: 260 calibration photos followed by a frozen 340-photo holdout. Previous first-five-per-class photos are excluded. Threshold selection uses only calibration data. Ramen is scored only at family level.

See `evaluation/results/optimization_report.md` and `evaluation/results/clip_comparison.json` for results, individual predictions, limitations and sampling details. These are fixed dataset subsets; do not present them as overall real-world accuracy.

`Choob_Recognition_Optimized.ipynb` is a clean Colab entry point containing the same recognizer and comparison runner. Use a fresh CPU runtime and run its cells in order. Its opening summary records the completed run; code outputs are deliberately empty until it is executed again.

To reproduce in Colab with `recognition.py` in the current directory and the original `model` / `processor` loaded:

```python
exec(open("evaluation/run_clip_comparison.py").read())
summary, records = run_comparison(model, processor)
```

Use a fresh output directory for an intentional new experiment. A completed comparison is protected against accidental overwrite. Source photos are downloaded to that runtime and are not bundled with this project.

Regression checks use synthetic fixtures and do not download weights (27 checks currently pass):

```bash
python -m unittest discover -s tests -v
```

## Recommendation data and rebuild

The current data is already included in `data/`. Keep the CSV, NPY and JSON manifest together; the backend checks hashes and matrix shape, and loads the embedding model revision recorded in the manifest. See `data/README.md` for the input contract and rebuild commands.

The completed extraction used **Codex-assisted annotations with exact source quotations**, followed by validation and a small AI semantic audit. It did **not** execute Qwen or fine-tune model weights. MiniLM embedding and preference inference were actually executed locally. The new `Choob_Recommendation_Pipeline.ipynb` and `build_recommendations.py` support either supplied annotations or a future Qwen2.5-1.5B-Instruct run. Original review text and annotation checkpoints are excluded from this application package.

`evaluation/results/recommendation_smoke.json` records actual MiniLM + Flask test-client inference for five different preferences, an embedding alignment spot check, and malformed/unsupported-request checks. It measures integration, not recommendation accuracy. The local browser was also checked for dessert recommendations and a dietary-request error. See `evaluation/results/recommendation_report.md` for details and remaining evaluation work.

## Collaboration

All five teammates work in the same GitHub repository using their existing collaborator access. Each person creates a branch from the latest `main`, makes changes, opens a pull request, and has another teammate review it before merging. After a merge, everyone updates their local `main` before starting the next branch.

| Person | Main handoff |
|---|---|
| 1: UI + flow | `index.html`; preserve API request and response fields |
| 2: Data processing | Clean review/catalog CSVs using `data/README.md` |
| 3: AI + recommendation | Model code, exports, manifest and model limitations |
| 4: Integration + deployment | Flask/HTML integration and shared hosted URL |
| 5: Evaluation + testing | Human-labeled relevance tests and end-to-end checks |

A localhost URL is only available on the computer running Flask. Collaborator access allows code collaboration; it does not create a shared live app. Future changes should be committed on a branch and merged through a reviewed pull request so teammates can pull the same version.

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
build_recommendations.py  Validated extraction, aggregation and aligned export
Choob_Recommendation_Pipeline.ipynb  Self-contained Colab rebuild entry point
recognition.py      CLIP prompt ensembles and scope decision
recognition_config.json  Frozen calibration threshold and vocabulary fingerprint
index.html          Original Choob UI (updated, no frameworks required)
evaluation/         Reproducible comparisons and recorded results
tests/              Recognition and recommendation regression checks
data/               Recommendation CSV, embeddings, manifest and input contract
requirements.txt    Python dependencies
Dockerfile          Deployment option
cache_models.py     Cache public model weights during Docker image construction
.dockerignore       Keep private inputs, local caches and environments out of images
.gitignore          Avoid accidental uploads
```
