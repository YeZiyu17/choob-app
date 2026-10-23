"""Choob CLIP inference: cached prompt ensembles and explicit scope checking.

Uses the original pretrained weights; no weight fine-tuning. Supported scores
rank nine dish families. A separate, broader vocabulary competes with those
families so an unsupported image need not be forced into the app's menu.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path

MODEL_ID = "openai/clip-vit-base-patch32"
VERSION = "clip-scope-v2"
BASELINE_LABELS = [
    "tonkotsu ramen", "shoyu ramen", "sushi", "dumplings", "fried rice",
    "pad thai", "pizza", "pasta", "hamburger", "tacos",
]
TEMPLATES = [
    "a photo of {}.", "a close-up photo of {}.",
    "a photo of a plate of {}.", "a restaurant photo of {}.",
]
# Ramen is intentionally a family label: the available evaluation labels do
# not establish reliable tonkotsu versus shoyu recognition.
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
# Fixed before the new calibration/test run. Food names use Food-101's public
# taxonomy, plus other foods and explicit non-food descriptions. This is a
# competing vocabulary, not a guarantee of open-world rejection.
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


def vocabulary_fingerprint():
    spec = {"version": VERSION, "model": MODEL_ID, "templates": TEMPLATES,
            "supported": SUPPORTED_DESCRIPTIONS, "background": BACKGROUND_DESCRIPTIONS}
    return sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()


def load_threshold(path=None):
    """A saved threshold is valid only for this exact prompt vocabulary."""
    path = Path(path) if path else Path(__file__).with_name("recognition_config.json")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("vocabulary_fingerprint") != vocabulary_fingerprint():
        raise ValueError("Recognition vocabulary changed; recalibrate before serving.")
    threshold = float(config["support_margin_threshold"])
    if not math.isfinite(threshold) or not -2 <= threshold <= 2:
        raise ValueError("Invalid recognition threshold")
    return threshold


class DishRecognizer:
    def __init__(self, model, processor, threshold=0.0):
        import torch
        import torch.nn.functional as F
        self.model, self.processor, self.threshold = model, processor, float(threshold)
        self.device = next(model.parameters()).device
        self.labels = list(SUPPORTED_DESCRIPTIONS)
        self.model.eval()
        self.groups = []
        descriptions = []
        for label in self.labels:
            first = len(descriptions)
            descriptions.extend(SUPPORTED_DESCRIPTIONS[label])
            self.groups.append((first, len(descriptions)))
        self.support_count = len(descriptions)
        descriptions.extend(BACKGROUND_DESCRIPTIONS)
        prompts = [template.format(name) for name in descriptions for template in TEMPLATES]
        text = self._encode_text(prompts)
        self.prototypes = F.normalize(text.reshape(len(descriptions), len(TEMPLATES), -1).mean(1), dim=-1)
        self.baseline_text = self._encode_text([f"a photo of {name}" for name in BASELINE_LABELS])
        self.logit_scale = float(model.logit_scale.detach().exp().cpu())

    def _encode_text(self, prompts, batch_size=64):
        import torch
        import torch.nn.functional as F
        rows = []
        with torch.inference_mode():
            for start in range(0, len(prompts), batch_size):
                inputs = self.processor(text=prompts[start:start + batch_size], padding=True, return_tensors="pt")
                inputs = {key: value.to(self.device) for key, value in inputs.items()}
                features = self.model.get_text_features(**inputs)
                rows.append(F.normalize(features, dim=-1).cpu())
        return torch.cat(rows)

    def encode_images(self, images, batch_size=16):
        import torch
        import torch.nn.functional as F
        rows = []
        with torch.inference_mode():
            for start in range(0, len(images), batch_size):
                inputs = self.processor(images=images[start:start + batch_size], return_tensors="pt")
                pixels = inputs["pixel_values"].to(self.device)
                features = self.model.get_image_features(pixel_values=pixels)
                rows.append(F.normalize(features, dim=-1).cpu())
        return torch.cat(rows)

    def score_features(self, features):
        import torch
        similarities = features.cpu() @ self.prototypes.T
        supported = torch.stack([similarities[:, start:end].max(dim=1).values for start, end in self.groups], dim=1)
        relative = (supported * self.logit_scale).softmax(dim=1)
        background, background_idx = similarities[:, self.support_count:].max(dim=1)
        rows = []
        for i in range(len(features)):
            order = supported[i].argsort(descending=True).tolist()
            best = float(supported[i, order[0]])
            rows.append({
                "top_3": [{"dish_name": self.labels[j], "relative_score": float(relative[i, j])} for j in order[:3]],
                "support_margin": best - float(background[i]),
                "support_similarity": best, "background_similarity": float(background[i]),
                "background_label": BACKGROUND_DESCRIPTIONS[int(background_idx[i])],
            })
        return rows

    def baseline_scores(self, features):
        scores = (features.cpu() @ self.baseline_text.T * self.logit_scale).softmax(dim=1)
        return [{"top_3": [{"dish_name": BASELINE_LABELS[j], "relative_score": float(row[j])}
                            for j in row.argsort(descending=True).tolist()[:3]]} for row in scores]

    def predict_from_scores(self, score, threshold=None):
        limit = self.threshold if threshold is None else float(threshold)
        accepted = score["support_margin"] >= limit
        suggestion = score["top_3"][0]["dish_name"]
        cuisine, category = CATEGORY_MAP[suggestion] if accepted else ("Unknown", "Unknown")
        return {
            "dish_name": suggestion.title() if accepted else "Unknown",
            "suggested_dish": suggestion.title(),
            "cuisine": cuisine, "category": category,
            "status": "supported" if accepted else "uncertain", "accepted": bool(accepted),
            "relative_score": round(score["top_3"][0]["relative_score"], 5),
            "alternatives": [{"dish_name": row["dish_name"].title(), "relative_score": round(row["relative_score"], 5)} for row in score["top_3"][1:]],
            "needs_user_confirmation": True, "supported_labels": self.labels,
            "model": "CLIP ViT-B/32 · prompt ensemble + scope check",
            "score_note": "Relative ranking among nine supported dish families; not calibrated confidence.",
            "message": ("Confirm or correct this suggested dish before collecting." if accepted else
                        "This photo may show an unsupported dish or an unclear image. Enter the dish name manually or try another photo."),
        }

    def predict(self, image):
        return self.predict_from_scores(self.score_features(self.encode_images([image]))[0])
