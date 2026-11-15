"""CHOOB Snap CLIP inference with calibrated legacy and broad review layers.

The original nine-family scope gate remains frozen to its real calibration.
Hundreds of additional candidate labels are scored independently and are always
presented as provisional, editable suggestions rather than calibrated accepts.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import tempfile

from food_vocabulary import FOOD_CANDIDATES


MODEL_ID = "openai/clip-vit-base-patch32"
VERSION = "clip-broad-suggestions-v1"
LEGACY_VERSION = "clip-scope-v2"
BASELINE_LABELS = [
    "tonkotsu ramen", "shoyu ramen", "sushi", "dumplings", "fried rice",
    "pad thai", "pizza", "pasta", "hamburger", "tacos",
]
TEMPLATES = [
    "a photo of {}.", "a close-up photo of {}.",
    "a photo of a plate of {}.", "a restaurant photo of {}.",
]

# Frozen verbatim from the real nine-family calibration.
SUPPORTED_DESCRIPTIONS = {
    "ramen": ["ramen", "Japanese ramen noodle soup", "tonkotsu ramen", "shoyu ramen"],
    "sushi": ["sushi", "Japanese sushi rolls", "nigiri sushi"],
    "dumplings": ["dumplings", "gyoza", "potstickers", "steamed Asian dumplings"],
    "fried rice": ["fried rice", "Chinese fried rice", "egg fried rice"],
    "pad thai": ["pad thai", "Thai stir fried rice noodles"],
    "pizza": ["pizza", "pepperoni pizza", "cheese pizza"],
    "pasta": ["pasta", "spaghetti bolognese", "spaghetti carbonara", "Italian pasta with sauce", "lasagna", "ravioli", "gnocchi", "macaroni and cheese"],
    "hamburger": ["hamburger", "cheeseburger", "beef burger in a bun"],
    "tacos": ["tacos", "Mexican tacos"],
}
BACKGROUND_DESCRIPTIONS = [
    "apple pie", "baby back ribs", "baklava", "beef carpaccio", "beef tartare",
    "beet salad", "beignets", "bibimbap", "bread pudding", "breakfast burrito",
    "bruschetta", "caesar salad", "cannoli", "caprese salad", "carrot cake",
    "ceviche", "cheesecake", "cheese plate", "chicken curry", "chicken quesadilla",
    "chicken wings", "chocolate cake", "chocolate mousse", "churros", "clam chowder",
    "club sandwich", "crab cakes", "creme brulee", "croque madame", "cup cakes",
    "deviled eggs", "donuts", "edamame", "eggs benedict", "escargots", "falafel",
    "filet mignon", "fish and chips", "foie gras", "french fries", "french onion soup",
    "french toast", "fried calamari", "frozen yogurt", "garlic bread", "Greek salad",
    "grilled cheese sandwich", "grilled salmon", "guacamole", "gyros", "hot and sour soup",
    "hot dog", "huevos rancheros", "hummus", "ice cream", "lobster bisque",
    "lobster roll sandwich", "macarons", "miso soup", "mussels", "nachos",
    "omelette", "onion rings", "oysters", "paella", "pancakes", "panna cotta",
    "Peking duck", "pho noodle soup", "pork chop", "poutine", "prime rib",
    "pulled pork sandwich", "red velvet cake", "risotto", "samosa", "sashimi",
    "scallops", "seaweed salad", "shrimp and grits", "spring rolls", "steak",
    "strawberry shortcake", "takoyaki", "tiramisu", "tuna tartare", "waffles",
    "fresh fruit", "a vegetable salad", "a slice of cake", "a bowl of soup",
    "a cup of coffee", "a glass of juice", "a bottle of water",
    "a dog", "a cat", "a person", "a building", "a landscape", "a car",
    "a mobile phone", "a laptop computer", "a book", "a shoe", "an empty plate",
    "a screenshot with text", "a non-food object",
]
CATEGORY_MAP = {
    "ramen": ("Japanese", "Noodles"), "sushi": ("Japanese", "Seafood"),
    "dumplings": ("Chinese / Asian", "Dumplings"), "fried rice": ("Asian", "Rice Dishes"),
    "pad thai": ("Thai", "Noodles"), "pizza": ("Italian", "Pizza"),
    "pasta": ("Italian", "Pasta"), "hamburger": ("American", "Sandwiches & Burgers"),
    "tacos": ("Mexican", "Other"),
}

# Genuinely non-food competitors for the expanded layer. Other foods are no
# longer treated as background merely because they are outside the original 9.
NON_FOOD_DESCRIPTIONS = [
    "a dog", "a cat", "a bird", "a person", "a hand", "a face", "a crowd of people",
    "a building", "a room", "a kitchen", "a restaurant interior", "a landscape", "a beach",
    "a road", "a car", "a bicycle", "a mobile phone", "a laptop computer", "a television",
    "a book", "a sheet of paper", "a sign", "a screenshot with text", "a menu with text",
    "a shoe", "clothing", "a bag", "a flower", "a plant", "a toy", "a tool",
    "an empty plate", "an empty bowl", "an empty table", "a non-food object",
    "a blurry unrecognizable image", "an abstract pattern", "a solid color image",
]


def _jsonable_candidates():
    return {
        key: {"aliases": list(value["aliases"]), "cuisine": value["cuisine"], "category": value["category"]}
        for key, value in FOOD_CANDIDATES.items()
    }


def calibrated_vocabulary_fingerprint():
    spec = {"version": LEGACY_VERSION, "model": MODEL_ID, "templates": TEMPLATES,
            "supported": SUPPORTED_DESCRIPTIONS, "background": BACKGROUND_DESCRIPTIONS}
    return sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def vocabulary_fingerprint():
    spec = {"version": VERSION,
            "calibrated_vocabulary_fingerprint": calibrated_vocabulary_fingerprint(),
            "candidates": _jsonable_candidates(), "non_food": NON_FOOD_DESCRIPTIONS}
    return sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def load_recognition_config(path=None):
    """Validate the frozen gate and explicitly provisional broad policy."""
    path = Path(path) if path else Path(__file__).with_name("recognition_config.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("vocabulary_fingerprint") != vocabulary_fingerprint():
        raise ValueError("Recognition vocabulary changed; update and evaluate its configuration before serving.")
    legacy = config.get("legacy_calibrated_gate", {})
    if legacy.get("vocabulary_fingerprint") != calibrated_vocabulary_fingerprint():
        raise ValueError("Calibrated recognition vocabulary changed; recalibrate before serving.")
    threshold = float(legacy.get("support_margin_threshold", float("nan")))
    if not math.isfinite(threshold) or not -2 <= threshold <= 2:
        raise ValueError("Invalid calibrated recognition threshold")
    policy = config.get("expanded_suggestion_policy", {})
    if policy.get("calibration_status") != "provisional_unvalidated":
        raise ValueError("Expanded suggestions must declare their calibration status.")
    for key in ("minimum_food_similarity", "minimum_food_over_non_food_margin",
                "minimum_label_separation"):
        value = float(policy.get(key, float("nan")))
        if not math.isfinite(value) or not -1 <= value <= 1:
            raise ValueError(f"Invalid expanded suggestion policy: {key}")
    return config


def load_threshold(path=None):
    """Return only the threshold tied to the unchanged nine-family gate."""
    return float(load_recognition_config(path)["legacy_calibrated_gate"]["support_margin_threshold"])


def _default_cache_dir():
    override = os.environ.get("CHOOB_TEXT_CACHE")
    if override:
        return Path(override)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "choob"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "choob"


class DishRecognizer:
    def __init__(self, model, processor, threshold=0.0, suggestion_policy=None, cache_dir=None):
        import torch

        self.model, self.processor, self.threshold = model, processor, float(threshold)
        self.device = next(model.parameters()).device
        self.model.eval()
        self.labels = list(SUPPORTED_DESCRIPTIONS)
        self.suggestion_policy = {"minimum_food_similarity": 0.23,
                                  "minimum_food_over_non_food_margin": 0.01,
                                  "minimum_label_separation": 0.012,
                                  **(suggestion_policy or {})}

        self.groups, legacy_descriptions = self._description_groups(SUPPORTED_DESCRIPTIONS)
        self.support_count = len(legacy_descriptions)
        legacy_descriptions.extend(BACKGROUND_DESCRIPTIONS)
        self.candidate_labels = list(FOOD_CANDIDATES)
        candidate_descriptions = {label: list(FOOD_CANDIDATES[label]["aliases"])
                                  for label in self.candidate_labels}
        self.candidate_groups, expanded_descriptions = self._description_groups(candidate_descriptions)

        arrays = self._load_or_build_text_arrays(legacy_descriptions, expanded_descriptions, cache_dir)
        self.prototypes = torch.from_numpy(arrays["legacy"])
        self.candidate_prototypes = torch.from_numpy(arrays["candidates"])
        self.non_food_prototypes = torch.from_numpy(arrays["non_food"])
        self.baseline_text = torch.from_numpy(arrays["baseline"])
        self.logit_scale = float(model.logit_scale.detach().exp().cpu())

    @staticmethod
    def _description_groups(mapping):
        groups, descriptions = [], []
        for aliases in mapping.values():
            first = len(descriptions)
            descriptions.extend(aliases)
            groups.append((first, len(descriptions)))
        return groups, descriptions

    def _load_or_build_text_arrays(self, legacy, candidates, cache_dir):
        import numpy as np
        import torch.nn.functional as F

        expected = {"legacy": len(legacy), "candidates": len(candidates),
                    "non_food": len(NON_FOOD_DESCRIPTIONS), "baseline": len(BASELINE_LABELS)}
        root = _default_cache_dir() if cache_dir is None else Path(cache_dir)
        cache_path = root / f"clip-text-{vocabulary_fingerprint()}.npz"
        try:
            with np.load(cache_path, allow_pickle=False) as cached:
                arrays = {name: cached[name] for name in expected}
            if all(array.ndim == 2 and array.shape[0] == expected[name]
                   for name, array in arrays.items()):
                return arrays
        except (OSError, KeyError, ValueError):
            pass

        def prototypes(descriptions):
            prompts = [template.format(name) for name in descriptions for template in TEMPLATES]
            text = self._encode_text(prompts)
            return F.normalize(text.reshape(len(descriptions), len(TEMPLATES), -1).mean(1), dim=-1)

        arrays = {"legacy": prototypes(legacy).numpy(),
                  "candidates": prototypes(candidates).numpy(),
                  "non_food": prototypes(NON_FOOD_DESCRIPTIONS).numpy(),
                  "baseline": self._encode_text([f"a photo of {name}" for name in BASELINE_LABELS]).numpy()}
        temp_path = None
        try:
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=root, suffix=".npz", delete=False) as temporary:
                temp_path = Path(temporary.name)
            np.savez_compressed(temp_path, **arrays)
            os.replace(temp_path, cache_path)
        except OSError:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
        return arrays

    def _encode_text(self, prompts, batch_size=64):
        import torch
        import torch.nn.functional as F
        rows = []
        with torch.inference_mode():
            for start in range(0, len(prompts), batch_size):
                inputs = self.processor(text=prompts[start:start + batch_size], padding=True, return_tensors="pt")
                inputs = {key: value.to(self.device) for key, value in inputs.items()}
                rows.append(F.normalize(self.model.get_text_features(**inputs), dim=-1).cpu())
        return torch.cat(rows)

    def encode_images(self, images, batch_size=16):
        import torch
        import torch.nn.functional as F
        rows = []
        with torch.inference_mode():
            for start in range(0, len(images), batch_size):
                inputs = self.processor(images=images[start:start + batch_size], return_tensors="pt")
                pixels = inputs["pixel_values"].to(self.device)
                rows.append(F.normalize(self.model.get_image_features(pixel_values=pixels), dim=-1).cpu())
        return torch.cat(rows)

    def score_features(self, features):
        import torch
        features = features.cpu()
        similarities = features @ self.prototypes.T
        supported = torch.stack([similarities[:, start:end].max(dim=1).values
                                 for start, end in self.groups], dim=1)
        relative = (supported * self.logit_scale).softmax(dim=1)
        background, background_idx = similarities[:, self.support_count:].max(dim=1)

        candidate_aliases = features @ self.candidate_prototypes.T
        candidates = torch.stack([candidate_aliases[:, start:end].max(dim=1).values
                                  for start, end in self.candidate_groups], dim=1)
        non_food, non_food_idx = (features @ self.non_food_prototypes.T).max(dim=1)

        rows = []
        for i in range(len(features)):
            order = supported[i].argsort(descending=True).tolist()
            candidate_order = candidates[i].argsort(descending=True).tolist()
            best = float(supported[i, order[0]])
            suggestion_similarity = float(candidates[i, candidate_order[0]])
            suggestion_separation = suggestion_similarity - float(candidates[i, candidate_order[1]])
            food_margin = suggestion_similarity - float(non_food[i])
            calibrated_accepted = best - float(background[i]) >= self.threshold
            suggestion_filter_reasons = []
            if suggestion_similarity < float(self.suggestion_policy["minimum_food_similarity"]):
                suggestion_filter_reasons.append("food_similarity")
            if food_margin < float(self.suggestion_policy["minimum_food_over_non_food_margin"]):
                suggestion_filter_reasons.append("food_over_non_food_margin")
            suggestion_useful = not suggestion_filter_reasons
            legacy_label = self.labels[order[0]]
            expanded_label = self.candidate_labels[candidate_order[0]]
            expanded_adds_information = (
                suggestion_useful
                and expanded_label != legacy_label
                and suggestion_separation >= float(self.suggestion_policy["minimum_label_separation"])
            )
            review_label = (expanded_label if expanded_adds_information else
                            legacy_label if calibrated_accepted else
                            expanded_label if suggestion_useful else None)
            review_mode = ("provisional" if review_label and (not calibrated_accepted or expanded_adds_information)
                           else "calibrated" if review_label else "none")
            rows.append({
                "top_3": [{"dish_name": self.labels[j], "relative_score": float(relative[i, j])}
                          for j in order[:3]],
                "support_margin": best - float(background[i]), "support_similarity": best,
                "background_similarity": float(background[i]),
                "background_label": BACKGROUND_DESCRIPTIONS[int(background_idx[i])],
                "suggestion_top_3": [{"dish_name": self.candidate_labels[j],
                                      "similarity": float(candidates[i, j])}
                                     for j in candidate_order[:3]],
                "suggestion_similarity": suggestion_similarity,
                "suggestion_separation": suggestion_separation,
                "food_over_non_food_margin": food_margin,
                "non_food_similarity": float(non_food[i]),
                "non_food_label": NON_FOOD_DESCRIPTIONS[int(non_food_idx[i])],
                "calibrated_accepted": calibrated_accepted,
                "suggestion_useful": suggestion_useful,
                "suggestion_filter_reasons": suggestion_filter_reasons,
                "review_label": review_label,
                "review_mode": review_mode,
            })
        return rows

    def baseline_scores(self, features):
        scores = (features.cpu() @ self.baseline_text.T * self.logit_scale).softmax(dim=1)
        return [{"top_3": [{"dish_name": BASELINE_LABELS[j], "relative_score": float(row[j])}
                            for j in row.argsort(descending=True).tolist()[:3]]} for row in scores]

    def predict_from_scores(self, score, threshold=None):
        limit = self.threshold if threshold is None else float(threshold)
        calibrated_gate = score.get("calibrated_accepted", score["support_margin"] >= limit)
        legacy_name = score["top_3"][0]["dish_name"]
        suggestions = score.get("suggestion_top_3", score.get("fallback_top_3", []))
        useful = bool(score.get("suggestion_useful"))
        review_label = score.get("review_label")
        review_mode = score.get("review_mode")
        provisional_name = (review_label if review_mode == "provisional" else
                            suggestions[0]["dish_name"] if useful and suggestions and not calibrated_gate else None)
        calibrated = calibrated_gate and review_mode != "provisional"
        if calibrated:
            dish_name = review_label or legacy_name
            cuisine, category = CATEGORY_MAP[dish_name]
            status, mode = "supported", "calibrated_supported"
        elif provisional_name:
            dish_name = provisional_name
            metadata = FOOD_CANDIDATES.get(dish_name.casefold(), {})
            cuisine, category = metadata.get("cuisine", "Unknown"), metadata.get("category", "Unknown")
            status, mode = "suggestion", "provisional_food_candidate"
        else:
            dish_name, cuisine, category = "Unknown", "Unknown", "Unknown"
            status, mode = "uncertain", "no_useful_food_suggestion"
        display_name = dish_name.title() if dish_name != "Unknown" else dish_name
        return {
            "dish_name": display_name, "suggested_dish": display_name,
            "cuisine": cuisine, "category": category, "status": status,
            "accepted": bool(calibrated), "reviewable": bool(calibrated or provisional_name),
            "relative_score": round(score["top_3"][0]["relative_score"], 5) if calibrated else None,
            "alternatives": [], "needs_user_confirmation": True,
            "supported_labels": self.labels, "candidate_label_count": len(FOOD_CANDIDATES),
            "suggestion_mode": mode, "model": "CLIP ViT-B/32 · prompt ensembles",
            "score_note": ("Calibrated only for the original nine-family scope gate; confirm or rename the dish."
                           if calibrated else
                           "Provisional zero-shot food candidate; it is not a probability or calibrated identification."
                           if provisional_name else
                           "No useful food candidate passed the provisional food-versus-non-food checks."),
            "message": ("Confirm or correct this suggested dish before logging."
                        if calibrated else
                        "Possible food suggestion—confirm, rename, or remove it before logging."
                        if provisional_name else
                        "Snap could not identify a useful food suggestion. Enter the dish manually or try another photo."),
        }

    def predict(self, image):
        return self.predict_from_scores(self.score_features(self.encode_images([image]))[0])
