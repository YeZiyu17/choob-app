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
from datetime import datetime
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


def recommendation_summary():
    """Read public build metadata without loading CSVs, vectors or model weights."""
    raw = (DATA / "choob_recommendation_manifest.json").read_bytes()
    manifest = json.loads(raw)
    if not isinstance(manifest, dict):
        raise ValueError("Recommendation manifest must be an object")

    def count(key):
        value = manifest[key]
        if type(value) is not int or value < 0:
            raise ValueError("Invalid recommendation manifest count")
        return value

    fields = (
        "input_reviews", "selected_reviews", "input_restaurants", "selected_restaurants",
        "restaurants_with_recommendations",
        "extracted_review_dish_records", "recommendation_rows", "failed_reviews",
    )
    summary = {key: count(key) for key in fields}
    catalog_size = manifest["restaurant_catalog_size"]
    if catalog_size is not None and (type(catalog_size) is not int or catalog_size < 0):
        raise ValueError("Invalid recommendation catalog size")
    summary["restaurant_catalog_size"] = catalog_size
    statuses = manifest["review_status_counts"]
    if (not isinstance(statuses, dict)
            or not set(statuses).issubset({"processed", "zero_dishes", "no_eligible_dishes", "failed"})
            or any(type(value) is not int or value < 0 for value in statuses.values())):
        raise ValueError("Invalid recommendation review statuses")
    if (sum(statuses.values()) != summary["selected_reviews"]
            or statuses.get("failed", 0) != summary["failed_reviews"]
            or summary["selected_reviews"] > summary["input_reviews"]
            or summary["selected_restaurants"] > summary["input_restaurants"]
            or (catalog_size is not None and summary["input_restaurants"] > catalog_size)
            or summary["restaurants_with_recommendations"] > summary["selected_restaurants"]
            or summary["recommendation_rows"] > summary["extracted_review_dish_records"]):
        raise ValueError("Recommendation manifest counts are inconsistent")
    for key in ("source_sha256", "config_sha256"):
        if not isinstance(manifest[key], str) or not re.fullmatch(r"[a-f0-9]{64}", manifest[key]):
            raise ValueError("Invalid recommendation build hash")
    for key in ("extraction_route", "extraction_model", "embedding_model"):
        value = manifest[key]
        if (not isinstance(value, str) or not value.strip() or len(value) > 200
                or "\n" in value or "\r" in value or Path(value).is_absolute()
                or re.match(r"^[A-Za-z]:[\\/]", value)):
            raise ValueError("Invalid recommendation model metadata")
        summary[key] = value
    if type(manifest["human_evaluation_completed"]) is not bool:
        raise ValueError("Invalid human evaluation flag")
    created = manifest["created_utc"]
    if not isinstance(created, str) or datetime.fromisoformat(created).tzinfo is None:
        raise ValueError("Missing timezone in recommendation build date")
    summary.update(
        manifest_sha256=sha256(raw).hexdigest(),
        source_version=manifest["source_sha256"][:12],
        build_version=manifest["config_sha256"][:12],
        created_utc=created,
        zero_dish_reviews=statuses.get("zero_dishes", 0) + statuses.get("no_eligible_dishes", 0),
        human_evaluation_completed=manifest["human_evaluation_completed"],
    )
    return summary


@app.get("/api/recommendation-summary")
def recommendation_summary_api():
    try:
        response = jsonify(recommendation_summary())
        response.headers["Cache-Control"] = "no-store"
        return response
    except (OSError, ValueError, KeyError, TypeError):
        return jsonify(error="Current recommendation build metadata is unavailable. Check the saved manifest."), 503


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


def load_recommender():
    """Reuse only the currently published export version in this data directory."""
    directory = Path(DATA).resolve()
    csv = directory / "choob_recommendation_data.csv"
    npy = directory / "choob_dish_embeddings.npy"
    if not csv.is_file() or not npy.is_file():
        raise FileNotFoundError(
            "Recommendation data is missing. In the Colab notebook, run the final export cell and copy "
            "choob_recommendation_data.csv and choob_dish_embeddings.npy into the data/ folder."
        )
    try:
        manifest_raw = (directory / "choob_recommendation_manifest.json").read_bytes()
    except FileNotFoundError:
        manifest_raw = None
    if manifest_raw is not None:
        version = ("manifest", sha256(manifest_raw).hexdigest())
    else:
        # Older notebook exports have no manifest. Replacement or in-place edits
        # must still invalidate the cache without hashing both files every query.
        version = ("legacy", *(
            (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            for stat in (csv.stat(), npy.stat())
        ))
    return _load_recommender_version(directory, version, manifest_raw)


@lru_cache(maxsize=1)
def _load_recommender_version(directory, version, manifest_raw):
    import numpy as np
    import pandas as pd

    csv = directory / "choob_recommendation_data.csv"
    npy = directory / "choob_dish_embeddings.npy"
    # Validate and parse the same byte snapshots, even if a build replaces files
    # while this request is loading. An incomplete published pair fails closed.
    csv_raw, npy_raw = csv.read_bytes(), npy.read_bytes()
    manifest = {}
    if manifest_raw is not None:
        manifest = json.loads(manifest_raw)
        for path, raw in ((csv, csv_raw), (npy, npy_raw)):
            if manifest.get("output_sha256", {}).get(path.name) != sha256(raw).hexdigest():
                raise ValueError("Recommendation exports do not match their build manifest. Copy all three files from the same run.")
    df = pd.read_csv(io.BytesIO(csv_raw))
    embeddings = np.load(io.BytesIO(npy_raw), allow_pickle=False)
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


# Preserve the public cache controls used by existing callers and tests.
load_recommender.cache_clear = _load_recommender_version.cache_clear
load_recommender.cache_info = _load_recommender_version.cache_info
load_recommender.cache_parameters = _load_recommender_version.cache_parameters


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
