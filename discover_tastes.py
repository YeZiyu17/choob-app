"""Taste profiles built from Passport ratings, for one diner or two people planning a meal.

The browser summarizes ratings it already stores (Snap saves a 1–5 rating on each dish) and sends
only cuisine names and low-rated dish names. Discover uses them to rank picks toward liked
cuisines, skip dishes someone rated low, and explain the match on each card.
"""

from __future__ import annotations

import re

from discover_chat import CUISINE_GROUPS

_MAX_CUISINES = 5
_MAX_DISLIKED = 20
_CUISINE_LABELS = {label.casefold(): label for label in CUISINE_GROUPS}
_NAME = re.compile(r"^[\w .'’-]{1,40}$", re.UNICODE)


def _short_text(value, limit):
    if not isinstance(value, str):
        return ""
    value = " ".join(value.split())
    return value if 0 < len(value) <= limit and any(c.isalpha() for c in value) else ""


def clean_taste_profile(value, *, named=False):
    """Keep known cuisines and short dish names; return None for a missing or unusable profile."""
    if not isinstance(value, dict):
        return None
    cuisines = []
    for cuisine in value.get("liked_cuisines") or ():
        label = _CUISINE_LABELS.get(cuisine.strip().casefold()) if isinstance(cuisine, str) else None
        if label and label not in cuisines:
            cuisines.append(label)
    disliked = []
    for dish in value.get("disliked_dishes") or ():
        name = _short_text(dish, 80)
        if name and name.casefold() not in {item.casefold() for item in disliked}:
            disliked.append(name)
    profile = {"liked_cuisines": cuisines[:_MAX_CUISINES], "disliked_dishes": disliked[:_MAX_DISLIKED]}
    if named:
        name = _short_text(value.get("name"), 40)
        if not name or not _NAME.match(name):
            return None
        profile["name"] = name
    if not profile["liked_cuisines"] and not profile["disliked_dishes"] and not named:
        return None
    return profile


def combine_tastes(mine, partner):
    """Merge one or two profiles into what the search uses, or None when there is nothing to use."""
    if not mine and not partner:
        return None
    mine = mine or {"liked_cuisines": [], "disliked_dishes": []}
    partner = partner or {"liked_cuisines": [], "disliked_dishes": []}
    shared = [cuisine for cuisine in mine["liked_cuisines"] if cuisine in partner["liked_cuisines"]]
    favored = shared + [cuisine for cuisine in (*mine["liked_cuisines"], *partner["liked_cuisines"])
                        if cuisine not in shared]
    disliked = list(dict.fromkeys([*mine["disliked_dishes"], *partner["disliked_dishes"]]))
    return {
        "favored_cuisines": list(dict.fromkeys(favored)),
        "disliked_dishes": disliked,
        "mine": mine["liked_cuisines"],
        "partner": partner["liked_cuisines"],
        "partner_name": partner.get("name", ""),
    }


def taste_note(tastes, cuisine):
    """Say whose ratings favor this dish's cuisine, e.g. "You and Amelia both like Japanese"."""
    if not tastes or not cuisine:
        return ""
    mine, theirs, name = cuisine in tastes["mine"], cuisine in tastes["partner"], tastes["partner_name"]
    if mine and theirs:
        return f"You and {name} both like {cuisine}"
    if theirs:
        return f"{name} likes {cuisine}"
    if mine:
        return f"You rated {cuisine} highly"
    return ""


def favored_rank(tastes, cuisine):
    """Lower is better: shared favorites first, then either person's, then everything else."""
    favored = tastes["favored_cuisines"] if tastes else []
    return favored.index(cuisine) if cuisine in favored else len(favored)
