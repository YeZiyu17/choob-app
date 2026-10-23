# Choob — Shared Working AI Prototype

This project preserves the group's **original Choob HTML UI**, adds real food-photo upload and a dynamically populated Discover panel, and supplies Python endpoints based on the same models/logic as `Choob_AI_Dish_Recognition.ipynb`.

## What is actually live?

- **Snap**: Upload a new food image. The original pretrained **CLIP ViT-B/32** weights now use four prompt templates, dish synonyms, cached text features and competing background categories. Nine supported dish families include generic **ramen**; tonkotsu/shoyu subtypes are not asserted. A calibrated scope check can return **Unknown**. The UI requires confirmation or a manually entered dish name and makes clear that relative scores are **not calibrated probabilities**.
- **Discover**: Enter a preference. The server uses **Sentence-Transformers all-MiniLM-L6-v2**, the exported Yelp-derived dish dataset and embeddings, and the notebook's 85% similarity + 15% sentiment formula to calculate new rankings. Requires the two data files below.
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

Policy regression checks do not download weights:

```bash
python -m unittest discover -s tests -v
```

## To turn on live recommendations

In `Choob_AI_Dish_Recognition.ipynb`, run the final export cell. Copy both to `data/`:
- `choob_recommendation_data.csv`
- `choob_dish_embeddings.npy`

They MUST come from the same execution for indexing to match. See `data/README.md`.

## Collaboration

1. Upload this project's files (keep the directory structure) to the **same GitHub repository**.
2. Invite all four teammates as collaborators.
3. Agree on one owner who integrates PRs into `main` and maintains the deploy.
4. Make small branches (`feature/photo`, `feature/recommend`, `feature/passport`, `test/evaluation`).
5. Review and test branches before merging. Never upload API keys or unlicensed private data.

## Deployment

This is **Flask + HTML, not a Streamlit app**. Streamlit Community Cloud is not the correct deployment target for this Flask project. An ordinary Python app host (e.g. Render), or a Docker-enabled host (e.g. Hugging Face Spaces Docker) can serve both HTML and endpoints through one URL.

The bundled `Dockerfile` listens on port 7860. Hosting services vary in RAM, disk and CPU limits; verify the environment can run CLIP and MiniLM before the live demo. Free CPU deployment may experience slow cold starts. A GPU is NOT required for CLIP or MiniLM but improves speed.

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
recognition.py      CLIP prompt ensembles and scope decision
recognition_config.json  Frozen calibration threshold and vocabulary fingerprint
index.html          Original Choob UI (updated, no frameworks required)
evaluation/         Reproducible comparisons and recorded results
tests/              Scope-policy regression checks
data/README.md      How to export model data from Colab
requirements.txt    Python dependencies
Dockerfile          Deployment option
.gitignore          Avoid accidental uploads
```
