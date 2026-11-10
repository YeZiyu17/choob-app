"""Suggest distinct dish families from separate regions of a meal photo."""
from __future__ import annotations

from itertools import combinations


# Halves and quadrants at two sizes let a dish straddling a crop edge get
# a second view. These windows describe where we looked in the photo.
_WINDOWS = (
    (0, 0, 0.55, 1), (0.45, 0, 1, 1), (0, 0, 1, 0.55), (0, 0.45, 1, 1),
    (0, 0, 0.55, 0.55), (0.45, 0, 1, 0.55),
    (0, 0.45, 0.55, 1), (0.45, 0.45, 1, 1),
    (0, 0, 0.49, 0.49), (0.51, 0, 1, 0.49),
    (0, 0.51, 0.49, 1), (0.51, 0.51, 1, 1),
)
_REGION_MARGIN = 0.012
_REGION_RELATIVE_SCORE = 0.68
_REGION_SIMILARITY = 0.22


def _overlap(left, right):
    """Intersection as a fraction of the smaller window."""
    width = max(0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0, min(left[3], right[3]) - max(left[1], right[1]))
    left_area = (left[2] - left[0]) * (left[3] - left[1])
    right_area = (right[2] - right[0]) * (right[3] - right[1])
    return width * height / min(left_area, right_area)


def _regional_dishes(scores, margin, primary):
    # Each candidate is the winner of a distinct crop and must win a second,
    # overlapping crop. Runners-up from one crop are never treated as dishes.
    candidates = [
        (region, score) for region, score in zip(_WINDOWS, scores)
        if score["support_margin"] >= margin
        and score["support_similarity"] >= _REGION_SIMILARITY
        and score["top_3"][0]["relative_score"] >= _REGION_RELATIVE_SCORE
    ]
    corroborated = [
        candidate for candidate in candidates
        if any(
            other is not candidate and _label(candidate) == _label(other)
            and _overlap(candidate[0], other[0]) >= 0.5
            for other in candidates
        )
    ]
    # Pick the best set of up to three distinct, spatially separated winners.
    # An accepted whole-photo dish is kept whenever a regional set is emitted.
    for count in (3, 2):
        sets = [
            group for group in combinations(corroborated, count)
            if (primary is None or primary in {_label(item) for item in group})
            and all(
                _label(a) != _label(b) and _overlap(a[0], b[0]) <= 0.2
                for a, b in combinations(group, 2)
            )
        ]
        if sets:
            return sorted(
                max(sets, key=lambda group: sum(row[1]["support_margin"] for row in group)),
                key=lambda row: (_label(row) != primary, -row[1]["support_margin"]),
            )
    return []


def _label(candidate):
    return candidate[1]["top_3"][0]["dish_name"]


def _dish(prediction, region=None):
    result = {
        key: prediction[key]
        for key in ("dish_name", "cuisine", "category", "relative_score")
    }
    if region is not None:
        result["region"] = list(region)
    return result


def recognize_meal(recognizer, image):
    """Return the existing single-result fields and zero or more dish suggestions."""
    views = [image]
    short_edge, long_edge = sorted(image.size)
    if short_edge >= 128 and long_edge <= 3 * short_edge:
        thumbnail = image.copy()
        thumbnail.thumbnail((896, 896))
        width, height = thumbnail.size
        views.extend(
            thumbnail.crop((round(left * width), round(top * height),
                            round(right * width), round(bottom * height)))
            for left, top, right, bottom in _WINDOWS
        )
    scores = recognizer.score_features(recognizer.encode_images(views))
    whole = recognizer.predict_from_scores(scores[0])
    primary = scores[0]["top_3"][0]["dish_name"] if whole["accepted"] else None
    regions = _regional_dishes(scores[1:], max(recognizer.threshold, _REGION_MARGIN), primary)
    if regions:
        predictions = [recognizer.predict_from_scores(score) for _, score in regions]
        return {
            **(whole if whole["accepted"] else predictions[0]),
            "recognition_mode": "multi",
            "dishes": [_dish(prediction, region) for (region, _), prediction in zip(regions, predictions)],
            "message": "Review the dishes suggested from different areas of this photo.",
        }
    return {**whole, "recognition_mode": "single", "dishes": [_dish(whole)] if whole["accepted"] else []}
