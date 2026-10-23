# Choob — Shared Working AI Prototype

This project preserves the group's **original Choob HTML UI**, adds real food-photo upload and a dynamically populated Discover panel, and supplies Python endpoints based on the same models/logic as `Choob_AI_Dish_Recognition.ipynb`.

## What is actually live?

- **Snap**: Upload a new food image. A server-side pretrained **CLIP ViT-B/32** model compares the photo against the notebook's ten candidate dish labels and returns a ranked result. The UI makes clear that relative softmax scores are **not calibrated probabilities**. User can correct the label and collect the dish.
- **Discover**: Enter a preference. The server uses **Sentence-Transformers all-MiniLM-L6-v2**, the exported Yelp-derived dish dataset and embeddings, and the notebook's 85% similarity + 15% sentiment formula to calculate new rankings. Requires the two data files below.
- **Collect**: Saved dishes persist locally in the same browser via `localStorage`. There is **no multi-user account storage** yet.
- **Connect**, sample restaurant, sample challenges and results screen: illustrative UI, **not live community data**. The evaluation screen shows previously recorded Colab results, not live test metrics.
- The notebook's GPU-intensive **Qwen2.5-VL-3B** is **not integrated**. Snap uses the simpler CLIP baseline until the group deploys a GPU endpoint or uses an API. Do not describe Snap as open-ended VLM identification.

## Quick start (local development)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:7860**. First image inference downloads CLIP weights and may take a while. The first recommendation downloads MiniLM weights. Both need internet and enough RAM.

Check connection: http://localhost:7860/api/status

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
index.html          Original Choob UI (updated, no frameworks required)
data/README.md      How to export model data from Colab
requirements.txt    Python dependencies
Dockerfile          Deployment option
.gitignore          Avoid accidental uploads
```
