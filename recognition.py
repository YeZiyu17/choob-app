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

# Broader zero-shot suggestions are evaluated only after the calibrated scope
# check rejects an image. They do not change supported-class acceptance or the
# saved calibration fingerprint. Every fallback still requires user confirmation.
FALLBACK_DESCRIPTIONS = {
    "hot pot": ["Chinese hot pot", "Sichuan hot pot", "a communal pot of broth with sliced meat and vegetables"],
    "oatmeal with fruit": ["oatmeal with berries and banana", "a bowl of porridge topped with fruit", "breakfast oatmeal"],
    "rice porridge": ["rice porridge", "Chinese congee", "a bowl of savory rice porridge"],
    "stew": ["a bowl of meat and vegetable stew", "slow cooked stew", "a rustic stew in a pot"],
    "barbecue": ["barbecue meat", "grilled barbecue platter", "Chinese barbecue"],
    "bibimbap": ["Korean bibimbap rice bowl", "rice with vegetables and egg"],
    "pho": ["Vietnamese pho noodle soup", "beef pho with herbs"],
    "curry": ["curry with rice", "a bowl of chicken curry", "a rich savory curry"],
    "noodle soup": ["Asian noodle soup", "noodles in broth with vegetables and meat"],
    "stir-fried noodles": ["stir fried noodles", "chow mein", "lo mein noodles"],
    "spring rolls": ["spring rolls", "fried vegetable spring rolls"],
    "dim sum": ["Chinese dim sum", "a selection of dim sum dishes"],
    "peking duck": ["Peking duck", "Chinese roast duck"],
    "fried chicken": ["fried chicken", "crispy chicken pieces"],
    "chicken wings": ["chicken wings", "crispy fried chicken wings"],
    "steak": ["grilled steak", "sliced beef steak"],
    "grilled fish": ["grilled fish", "a whole cooked fish"],
    "salmon": ["grilled salmon fillet", "cooked salmon"],
    "salad": ["a fresh vegetable salad", "mixed green salad"],
    "sandwich": ["a sandwich", "a filled bread sandwich"],
    "burrito": ["Mexican burrito", "a wrapped burrito"],
    "quesadilla": ["cheese quesadilla", "Mexican quesadilla"],
    "nachos": ["nachos with cheese and toppings", "a plate of nachos"],
    "pancakes": ["a stack of pancakes", "breakfast pancakes with syrup"],
    "waffles": ["waffles", "breakfast waffles with fruit"],
    "omelette": ["an omelette", "egg omelette with vegetables"],
    "eggs benedict": ["eggs benedict", "poached eggs on English muffins"],
    "french toast": ["French toast", "sweet breakfast toast with fruit"],
    "soup": ["a bowl of soup", "vegetable soup", "meat soup"],
    "ice cream": ["ice cream", "a bowl of ice cream"],
    "cake": ["a slice of cake", "layer cake", "chocolate cake"],
    "cheesecake": ["cheesecake", "a slice of cheesecake"],
    "donuts": ["donuts", "glazed doughnuts"],
    "fruit bowl": ["a bowl of fresh fruit", "mixed fruit bowl"],
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
        self.fallback_labels = list(FALLBACK_DESCRIPTIONS)
        fallback_groups, fallback_descriptions = [], []
        for label in self.fallback_labels:
            first = len(fallback_descriptions)
            fallback_descriptions.extend(FALLBACK_DESCRIPTIONS[label])
            fallback_groups.append((first, len(fallback_descriptions)))
        fallback_prompts = [template.format(name) for name in fallback_descriptions for template in TEMPLATES]
        fallback_text = self._encode_text(fallback_prompts)
        fallback_prototypes = F.normalize(
            fallback_text.reshape(len(fallback_descriptions), len(TEMPLATES), -1).mean(1), dim=-1
        )
        self.fallback_prototypes = torch.stack([
            F.normalize(fallback_prototypes[start:end].mean(0), dim=-1)
            for start, end in fallback_groups
        ])
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
        fallback_similarities = features.cpu() @ self.fallback_prototypes.T
        rows = []
        for i in range(len(features)):
            order = supported[i].argsort(descending=True).tolist()
            fallback_order = fallback_similarities[i].argsort(descending=True).tolist()
            best = float(supported[i, order[0]])
            rows.append({
                "top_3": [{"dish_name": self.labels[j], "relative_score": float(relative[i, j])} for j in order[:3]],
                "support_margin": best - float(background[i]),
                "support_similarity": best, "background_similarity": float(background[i]),
                "background_label": BACKGROUND_DESCRIPTIONS[int(background_idx[i])],
                "fallback_top_3": [
                    {"dish_name": self.fallback_labels[j], "similarity": float(fallback_similarities[i, j])}
                    for j in fallback_order[:3]
                ],
            })
        return rows

    def baseline_scores(self, features):
        scores = (features.cpu() @ self.baseline_text.T * self.logit_scale).softmax(dim=1)
        return [{"top_3": [{"dish_name": BASELINE_LABELS[j], "relative_score": float(row[j])}
                            for j in row.argsort(descending=True).tolist()[:3]]} for row in scores]

    def predict_from_scores(self, score, threshold=None):
        limit = self.threshold if threshold is None else float(threshold)
        accepted = score["support_margin"] >= limit
        supported_suggestion = score["top_3"][0]["dish_name"]
        fallback_suggestion = score.get("fallback_top_3", [{}])[0].get("dish_name")
        suggestion = supported_suggestion if accepted else (fallback_suggestion or supported_suggestion)
        cuisine, category = CATEGORY_MAP[supported_suggestion] if accepted else ("Unknown", "Unknown")
        return {
            "dish_name": supported_suggestion.title() if accepted else "Unknown",
            "suggested_dish": suggestion.title(),
            "cuisine": cuisine, "category": category,
            "status": "supported" if accepted else "uncertain", "accepted": bool(accepted),
            "relative_score": round(score["top_3"][0]["relative_score"], 5),
            "alternatives": [{"dish_name": row["dish_name"].title(), "relative_score": round(row["relative_score"], 5)} for row in score["top_3"][1:]],
            "needs_user_confirmation": True, "supported_labels": self.labels,
            "suggestion_mode": "calibrated_supported" if accepted else "expanded_zero_shot",
            "model": "CLIP ViT-B/32 · prompt ensemble + scope check",
            "score_note": ("Relative ranking among nine calibrated dish families; not calibrated confidence." if accepted else
                           "Expanded zero-shot suggestion after calibrated rejection; confirmation is required."),
            "message": ("Confirm or correct this suggested dish before collecting." if accepted else
                        "This photo may show an unsupported dish or an unclear image. Enter the dish name manually or try another photo."),
        }

    def predict(self, image):
        return self.predict_from_scores(self.score_features(self.encode_images([image]))[0])
