"""Serve the original Choob HTML and connect it to real pretrained-model inference.

CLIP recognition: cached prompt ensembles plus calibrated scope checking.
Recommendation: reproduces notebook cell 42, requiring its exported CSV and .npy.
Models are lazily loaded to avoid downloading weights during application startup.
"""
from __future__ import annotations

from hashlib import sha256
import io
import json
import os
import re
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from recognition import CATEGORY_MAP, DishRecognizer, load_threshold

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


@app.get("/")
def home():
    return send_from_directory(str(BASE), "index.html")


@app.get("/api/status")
def status():
    return jsonify({
        "api": "running",
        "recognition": "CLIP prompt ensemble + scope check (weights download on first use)",
        "recognition_config_present": (BASE / "recognition_config.json").is_file(),
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


@lru_cache(maxsize=1)
def get_recognizer():
    threshold = load_threshold()
    model, processor = get_clip()
    return DishRecognizer(model, processor, threshold=threshold)


@app.post("/api/recognize")
def recognize():
    from PIL import Image, ImageOps, UnidentifiedImageError

    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return jsonify(error="Upload a JPG, PNG or WebP food photo."), 400
    try:
        raw = upload.read()
        if not raw:
            return jsonify(error="The uploaded file is empty."), 400
        image = Image.open(io.BytesIO(raw))
        image.verify()
        image = Image.open(io.BytesIO(raw))
        if image.width * image.height > 16_000_000:
            return jsonify(error="Please use an image smaller than 16 megapixels."), 400
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return jsonify(error="The file is not a valid image."), 400

    try:
        return jsonify(get_recognizer().predict(image))
    except Exception as exc:
        app.logger.exception("CLIP recognition error")
        return jsonify(error="Recognition backend unavailable. Check model downloads, server memory, and recognition_config.json."), 503


@lru_cache(maxsize=1)
def load_recommender():
    import numpy as np
    import pandas as pd

    csv = DATA / "choob_recommendation_data.csv"
    npy = DATA / "choob_dish_embeddings.npy"
    if not csv.is_file() or not npy.is_file():
        raise FileNotFoundError(
            "Recommendation data is missing. In the Colab notebook, run the final export cell and copy "
            "choob_recommendation_data.csv and choob_dish_embeddings.npy into the data/ folder."
        )
    manifest = {}
    manifest_path = DATA / "choob_recommendation_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for path in (csv, npy):
            if manifest.get("output_sha256", {}).get(path.name) != sha256(path.read_bytes()).hexdigest():
                raise ValueError("Recommendation exports do not match their build manifest. Copy all three files from the same run.")
    df = pd.read_csv(csv)
    embeddings = np.load(npy, allow_pickle=False)
    if embeddings.ndim != 2 or embeddings.shape != (len(df), 384):
        raise ValueError("Recommendation CSV and embedding rows do not match. Export both together from the same notebook run.")
    required = {"restaurant_name", "dish_name_normalized", "positive_count", "negative_count", "mixed_count", "neutral_count", "review_count"}
    if not required.issubset(df.columns):
        raise ValueError("Recommendation CSV missing required columns: " + ", ".join(sorted(required-set(df.columns))))
    if df.empty:
        raise ValueError("Recommendation dataset is empty.")
    if not np.issubdtype(embeddings.dtype, np.floating) or not np.isfinite(embeddings).all():
        raise ValueError("Dish embeddings must contain finite floating-point values.")
    if not np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, atol=1e-3):
        raise ValueError("Dish embeddings must be normalized to unit length.")
    for column in ("restaurant_name", "dish_name_normalized"):
        if df[column].isna().any() or df[column].astype(str).str.strip().eq("").any():
            raise ValueError("Recommendation names must be nonempty.")
    pair_keys = ["business_id" if "business_id" in df.columns else "restaurant_name", "dish_name_normalized"]
    if df.duplicated(pair_keys).any():
        raise ValueError("Recommendation restaurant-dish pairs must be unique.")
    counts = ["positive_count", "negative_count", "mixed_count", "neutral_count"]
    for column in counts + ["review_count"]:
        values = pd.to_numeric(df[column], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any() or (values != np.floor(values)).any():
            raise ValueError("Recommendation counts must be finite nonnegative integers.")
        df[column] = values
    if (df["review_count"] < 1).any() or not np.array_equal(df[counts].sum(axis=1), df["review_count"]):
        raise ValueError("Each restaurant-dish review must have exactly one sentiment label.")
    from sentence_transformers import SentenceTransformer

    model_options = {"device": "cpu"}
    if manifest.get("embedding_model_revision"):
        model_options["revision"] = manifest["embedding_model_revision"]
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", **model_options)
    return df, embeddings, model


@app.post("/api/recommend")
def recommend():
    import numpy as np

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Send a JSON object containing a food preference."), 400
    preference = payload.get("preference")
    if not isinstance(preference, str):
        return jsonify(error="preference must be text."), 400
    pref = preference.strip()
    if not pref or len(pref) > 1000:
        return jsonify(error="Please provide a food preference of 1–1000 characters."), 400
    # Semantic similarity cannot establish dietary suitability from review text.
    # Do not present a meat-containing semantic match as a verified diet result.
    if re.search(r"\b(vegetarian|vegan|meat[- ]free|no meat|without meat|halal|kosher|allerg(?:y|ies|ic)|gluten[- ]free|dairy[- ]free|nut[- ]free|peanut[- ]free)\b|素食|纯素|过敏|无麸质", pref, re.I):
        return jsonify(error="This version matches taste, but cannot verify dietary or allergy requirements from reviews. Try a dish or flavor preference."), 422
    top_n = payload.get("top_n", 5)
    if isinstance(top_n, bool) or not isinstance(top_n, int):
        return jsonify(error="top_n must be an integer."), 400
    top_n = max(1, min(10, top_n))

    try:
        df, embeddings, model = load_recommender()
        query = np.asarray(model.encode([pref], normalize_embeddings=True, convert_to_numpy=True))
        if query.shape != (1, 384) or not np.isfinite(query).all():
            raise ValueError("Preference embedding must be a finite 384-dimensional vector.")
        query_vec = query[0]
        similarity = embeddings @ query_vec
        pos = df["positive_count"].to_numpy(dtype=float)
        neg = df["negative_count"].to_numpy(dtype=float)
        mixed = df["mixed_count"].to_numpy(dtype=float)
        neutral = df["neutral_count"].to_numpy(dtype=float)
        total = pos + neg + mixed + neutral
        sentiment = (pos + 0.5 * mixed + 0.5 * neutral + 1) / (total + 2)
        scores = 0.85 * similarity + 0.15 * sentiment
        top = np.argsort(-scores, kind="stable")[:top_n]
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
