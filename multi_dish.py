"""Suggest distinct dish families from separate regions of a meal photo."""
from __future__ import annotations

_COARSE_WINDOWS = (
    (0, 0, 0.55, 1), (0.45, 0, 1, 1), (0, 0, 1, 0.55), (0, 0.45, 1, 1),
    (0, 0, 0.55, 0.55), (0.45, 0, 1, 0.55),
    (0, 0.45, 0.55, 1), (0.45, 0.45, 1, 1),
    (0, 0, 0.49, 0.49), (0.51, 0, 1, 0.49),
    (0, 0.51, 0.49, 1), (0.51, 0.51, 1, 1),
)


def _grid_windows(columns=3, rows=3, padding=0.035):
    """Return each grid cell plus a slightly expanded corroborating view."""
    windows = []
    for row in range(rows):
        for column in range(columns):
            exact = (column / columns, row / rows,
                     (column + 1) / columns, (row + 1) / rows)
            expanded = (
                max(0, exact[0] - padding), max(0, exact[1] - padding),
                min(1, exact[2] + padding), min(1, exact[3] + padding),
            )
            windows.extend((exact, expanded))
    return tuple(windows)


# Coarse views remain useful for ordinary table photos. Paired 3x3 cells add
# coverage for many small dishes without weakening any acceptance threshold.
_WINDOWS = (*_COARSE_WINDOWS, *_grid_windows())
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


def _candidate_filter(score, margin):
    reasons = []
    if score["support_margin"] < margin:
        reasons.append("support_margin")
    if score["support_similarity"] < _REGION_SIMILARITY:
        reasons.append("support_similarity")
    if score["top_3"][0]["relative_score"] < _REGION_RELATIVE_SCORE:
        reasons.append("relative_score")
    return reasons


def _regional_dishes(scores, margin, primary, trace=None):
    # Each candidate is the winner of a distinct crop and must win a second,
    # overlapping crop. Runners-up from one crop are never treated as dishes.
    candidates = [
        (region, score) for region, score in zip(_WINDOWS, scores)
        if not _candidate_filter(score, margin)
    ]
    corroborated = [
        candidate for candidate in candidates
        if any(
            other is not candidate and _label(candidate) == _label(other)
            and _overlap(candidate[0], other[0]) >= 0.5
            for other in candidates
        )
    ]
    # Choose at most one spatially separated region for each supported family.
    # Optimize coverage first and evidence strength second instead of imposing
    # the old arbitrary three-dish cap. There are only nine calibrated labels.
    options = {}
    for candidate in corroborated:
        options.setdefault(_label(candidate), []).append(candidate)
    if primary is not None and primary not in options:
        selected = []
    else:
        for label_options in options.values():
            label_options.sort(key=lambda item: item[1]["support_margin"], reverse=True)
        labels = sorted(options, key=lambda label: (
            label != primary, -options[label][0][1]["support_margin"], label,
        ))
        best = []
        best_key = (0, float("-inf"))

        def search(index, chosen):
            nonlocal best, best_key
            if len(chosen) + len(labels) - index < best_key[0]:
                return
            if index == len(labels):
                key = (len(chosen), sum(item[1]["support_margin"] for item in chosen))
                if key > best_key:
                    best, best_key = list(chosen), key
                return
            label = labels[index]
            if label != primary:
                search(index + 1, chosen)
            for candidate in options[label]:
                if all(_overlap(candidate[0], other[0]) <= 0.2 for other in chosen):
                    search(index + 1, [*chosen, candidate])

        search(0, [])
        selected = best if len(best) >= 2 else []
        selected.sort(key=lambda item: (_label(item) != primary, item[0][1], item[0][0]))

    if trace is not None:
        candidate_ids = {id(score) for _, score in candidates}
        corroborated_ids = {id(score) for _, score in corroborated}
        selected_ids = {id(score) for _, score in selected}
        trace.extend({
            "region": list(region),
            "winner": score["top_3"][0]["dish_name"],
            "top_3": score["top_3"],
            "support_margin": score["support_margin"],
            "support_similarity": score["support_similarity"],
            "background_label": score.get("background_label"),
            "background_similarity": score.get("background_similarity"),
            "fallback_top_3": score.get("fallback_top_3", []),
            "filter_reasons": _candidate_filter(score, margin),
            "candidate": id(score) in candidate_ids,
            "corroborated": id(score) in corroborated_ids,
            "selected": id(score) in selected_ids,
        } for region, score in zip(_WINDOWS, scores))
    return selected


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


def recognize_meal(recognizer, image, trace=None):
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
    regional_trace = [] if trace is not None else None
    regions = _regional_dishes(
        scores[1:], max(recognizer.threshold, _REGION_MARGIN), primary, regional_trace,
    )
    if trace is not None:
        trace({
            "whole": {
                "accepted": whole["accepted"],
                "winner": scores[0]["top_3"][0]["dish_name"],
                "top_3": scores[0]["top_3"],
                "support_margin": scores[0]["support_margin"],
                "support_similarity": scores[0]["support_similarity"],
                "background_label": scores[0].get("background_label"),
                "background_similarity": scores[0].get("background_similarity"),
                "fallback_top_3": scores[0].get("fallback_top_3", []),
            },
            "thresholds": {
                "support_margin": max(recognizer.threshold, _REGION_MARGIN),
                "support_similarity": _REGION_SIMILARITY,
                "relative_score": _REGION_RELATIVE_SCORE,
                "corroboration_overlap": 0.5,
                "separation_overlap": 0.2,
            },
            "regions": regional_trace,
            "selected": [_label(item) for item in regions],
        })
    if regions:
        predictions = [recognizer.predict_from_scores(score) for _, score in regions]
        return {
            **(whole if whole["accepted"] else predictions[0]),
            "recognition_mode": "multi",
            "dishes": [_dish(prediction, region) for (region, _), prediction in zip(regions, predictions)],
            "message": "Review the dishes suggested from different areas of this photo.",
        }
    return {**whole, "recognition_mode": "single", "dishes": [_dish(whole)] if whole["accepted"] else []}
