"""Serve the original Choob HTML and connect it to real pretrained-model inference.

CLIP recognition: reproduces the notebook's 10-candidate baseline, not open-ended VLM.
Recommendation: reproduces notebook cell 42, requiring its exported CSV and .npy.
Models are lazily loaded to avoid downloading weights during application startup.
"""
from __future__ import annotations

import ast
import io
import os
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

CANDIDATES = [
    "tonkotsu ramen", "shoyu ramen", "sushi", "dumplings", "fried rice",
    "pad thai", "pizza", "pasta", "hamburger", "tacos",
]
CATEGORY_MAP = {
    "tonkotsu ramen": ("Japanese", "Noodles"),
    "shoyu ramen": ("Japanese", "Noodles"),
    "sushi": ("Japanese", "Seafood"),
    "dumplings": ("Chinese / Asian", "Dumplings"),
    "fried rice": ("Asian", "Rice Dishes"),
    "pad thai": ("Thai", "Noodles"),
    "pizza": ("Italian", "Pizza"),
    "pasta": ("Italian", "Pasta"),
    "hamburger": ("American", "Sandwiches & Burgers"),
    "tacos": ("Mexican", "Other"),
}


@app.get("/")
def home():
    return send_from_directory(str(BASE), "index.html")


@app.get("/api/status")
def status():
    return jsonify({
        "api": "running",
        "recognition": "CLIP baseline available on first use (weights download required)",
        "recommendation_data_present": (DATA / "choob_recommendation_data.csv").is_file(),
        "recommendation_embeddings_present": (DATA / "choob_dish_embeddings.npy").is_file(),
    })


@lru_cache(maxsize=1)
def get_clip():
    from transformers import CLIPModel, CLIPProcessor
    model_id = "openai/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_id)
    processor = CLIPProcessor.from_pretrained(model_id)
    model.eval()
    return model, processor


@app.post("/api/recognize")
def recognize():
    import torch
    from PIL import Image, UnidentifiedImageError

    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return jsonify(error="Upload a JPG, PNG or WebP food photo."), 400
    try:
        raw = upload.read()
        if not raw:
            return jsonify(error="The uploaded file is empty."), 400
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        if image.width * image.height > 16_000_000:
            return jsonify(error="Please use an image smaller than 16 megapixels."), 400
    except (UnidentifiedImageError, OSError, ValueError):
        return jsonify(error="The file is not a valid image."), 400

    try:
        model, processor = get_clip()
        data = processor(
            text=[f"a photo of {x}" for x in CANDIDATES],
            images=image,
            return_tensors="pt",
            padding=True,
        )
        with torch.inference_mode():
            scores = model(**data).logits_per_image.softmax(dim=1)[0]
        ranked = sorted(zip(CANDIDATES, scores.tolist()), key=lambda x: x[1], reverse=True)
        best, score = ranked[0]
        cuisine, category = CATEGORY_MAP[best]
        return jsonify({
            "dish_name": best.title(),
            "cuisine": cuisine,
            "category": category,
            "relative_score": round(float(score), 5),
            "alternatives": [{"dish_name": n.title(), "relative_score": round(float(sc), 5)} for n, sc in ranked[1:3]],
            "needs_user_confirmation": True,
            "model": "CLIP ViT-B/32 (10 candidate labels)",
        })
    except Exception as exc:
        app.logger.exception("CLIP recognition error")
        return jsonify(error="CLIP model could not run. Confirm the server can download Hugging Face weights and has enough memory."), 503


@lru_cache(maxsize=1)
def load_recommender():
    import numpy as np
    import pandas as pd
    from sentence_transformers import SentenceTransformer

    csv = DATA / "choob_recommendation_data.csv"
    npy = DATA / "choob_dish_embeddings.npy"
    if not csv.is_file() or not npy.is_file():
        raise FileNotFoundError(
            "Recommendation data is missing. In the Colab notebook, run the final export cell and copy "
            "choob_recommendation_data.csv and choob_dish_embeddings.npy into the data/ folder."
        )
    df = pd.read_csv(csv)
    embeddings = np.load(npy, allow_pickle=False)
    if len(df) != len(embeddings):
        raise ValueError("Recommendation CSV and embedding rows do not match. Export both together from the same notebook run.")
    required = {"restaurant_name", "dish_name_normalized", "positive_count", "negative_count", "mixed_count", "neutral_count", "review_count"}
    if not required.issubset(df.columns):
        raise ValueError("Recommendation CSV missing required columns: " + ", ".join(sorted(required-set(df.columns))))
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    return df, embeddings, model


@app.post("/api/recommend")
def recommend():
    import numpy as np

    payload = request.get_json(silent=True) or {}
    pref = str(payload.get("preference") or "").strip()
    if not pref or len(pref) > 1000:
        return jsonify(error="Please provide a food preference of 1–1000 characters."), 400
    try:
        top_n = max(1, min(10, int(payload.get("top_n", 5))))
    except (TypeError, ValueError):
        return jsonify(error="top_n must be an integer."), 400

    try:
        df, embeddings, model = load_recommender()
        query_vec = model.encode([pref], normalize_embeddings=True, convert_to_numpy=True)[0]
        similarity = embeddings @ query_vec
        pos = df["positive_count"].to_numpy(dtype=float)
        neg = df["negative_count"].to_numpy(dtype=float)
        mixed = df["mixed_count"].to_numpy(dtype=float)
        neutral = df["neutral_count"].to_numpy(dtype=float)
        total = pos + neg + mixed + neutral
        sentiment = (pos + 0.5 * mixed + 0.5 * neutral + 1) / (total + 2)
        scores = 0.85 * similarity + 0.15 * sentiment
        top = np.argsort(-scores)[:top_n]
        results = []
        for idx in top:
            row = df.iloc[int(idx)]
            results.append({
                "dish_name": str(row["dish_name_normalized"]).title(),
                "restaurant_name": str(row["restaurant_name"]),
                "review_count": int(row["review_count"]),
                "score": round(float(scores[idx]), 4),
                "similarity": round(float(similarity[idx]), 4),
            })
        return jsonify(results=results, model="all-MiniLM-L6-v2 + Yelp review sentiment", note="Uncalibrated ranking scores; not probability of liking a dish")
    except FileNotFoundError as exc:
        return jsonify(error=str(exc)), 503
    except Exception:
        app.logger.exception("Recommendation error")
        return jsonify(error="Recommendation backend failed. Check data files and model downloads in the server logs."), 503


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Photo must be smaller than 8 MB."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "7860")), debug=False)
