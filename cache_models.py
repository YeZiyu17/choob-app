"""Cache the application's public CPU models while building its Docker image."""
from __future__ import annotations

import gc
import json
from pathlib import Path
import re


def main() -> None:
    from sentence_transformers import SentenceTransformer
    from transformers import CLIPModel, CLIPProcessor

    manifest_path = Path(__file__).resolve().parent / "data" / "choob_recommendation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    if manifest.get("embedding_model") != model_id:
        raise ValueError("The recommendation manifest must identify all-MiniLM-L6-v2.")
    revision = manifest.get("embedding_model_revision", "")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("The recommendation manifest must pin the embedding model commit.")

    print(f"Caching {model_id} at {revision}", flush=True)
    model = SentenceTransformer(model_id, revision=revision, device="cpu")
    del model
    gc.collect()

    clip_id = "openai/clip-vit-base-patch32"
    print(f"Caching {clip_id}", flush=True)
    model = CLIPModel.from_pretrained(clip_id)
    processor = CLIPProcessor.from_pretrained(clip_id)
    del model, processor
    gc.collect()
    print("Both application models are cached; runtime can use offline mode.", flush=True)


if __name__ == "__main__":
    main()
