"""Keep the Discover conversation grounded in supported review preferences."""
from __future__ import annotations

import json
from math import log1p
import re


CUISINE_GROUPS = {
    "Japanese": "Japanese/Sushi/Ramen",
    "Italian": "Italian/Pizza",
    "Mexican": "Mexican",
    "Thai": "Thai",
    "Chinese": "Chinese",
    "Korean": "Korean",
    "Vietnamese": "Vietnamese",
    "Indian": "Indian/South Asian",
    "American": "American/Burgers/Bars",
    "French": "French",
    "Mediterranean": "Greek/Mediterranean",
    "Middle Eastern": "Middle Eastern",
    "Caribbean": "Caribbean/Latin American",
    "Ethiopian": "Ethiopian/African",
    "Seafood": "Seafood",
    "BBQ": "BBQ",
    "Southern": "Soul Food/Southern",
}
TASTE_TERMS = {
    "Spicy": ("spicy", "spicey", "peppery", "spiciness"),
    "Crispy": ("crispy", "crunchy", "crisp", "crunchiness"),
    "Fresh & light": ("fresh", "light", "refreshing", "freshness"),
    "Rich & creamy": ("rich", "creamy", "buttery", "richly flavored"),
    "Sweet": ("sweet", "sweetness"),
    "Savory": ("savory", "savoury", "umami"),
    "Mild": ("mild", "not spicy", "non-spicy"),
}
CUISINE_OPTIONS = ("Japanese", "Italian", "Mexican", "Thai", "Chinese", "Korean", "Any cuisine")
TASTE_OPTIONS = ("Spicy", "Crispy", "Fresh & light", "Rich & creamy", "Sweet", "Any flavor")
CUISINES = (*CUISINE_GROUPS, "Any cuisine")
TASTES = (*TASTE_TERMS, "Any flavor")
CHINESE_REGIONS = ("Sichuan", "Hunan", "Cantonese")
_ANY_CHINESE_STYLE = "Any Chinese style"
_REGION_CHOICES = {label.casefold(): label for label in (*CHINESE_REGIONS, _ANY_CHINESE_STYLE)}

DIETARY_REQUEST = re.compile(
    r"\b(vegetarian|vegan|meat[- ]free|no meat|without meat|halal|kosher|allerg(?:y|ies|ic)|"
    r"celiac|gluten[- ]free|dairy[- ]free|nut[- ]free|peanut[- ]free|"
    r"(?:no|without)\s+(?:peanuts?|tree nuts?|gluten|dairy|shellfish))\b|素食|纯素|过敏|无麸质",
    re.I,
)
DIETARY_MESSAGE = (
    "This version matches taste, but cannot verify dietary or allergy requirements from reviews. "
    "Try a dish or flavor preference."
)

_KEYS = ("cuisine", "taste", "dish")
_EXACT_CHOICES = {
    **{label.casefold(): ("cuisine", label) for label in CUISINES},
    **{label.casefold(): ("taste", label) for label in TASTES},
}


def clean_preferences(values):
    """Accept only known options and a short literal dish name."""
    clean = dict.fromkeys(_KEYS, "")
    for key, labels in (("cuisine", CUISINES), ("taste", TASTES)):
        value = values.get(key)
        if isinstance(value, str):
            clean[key] = next((label for label in labels if value.strip().casefold() == label.casefold()), "")
    dish = values.get("dish")
    if isinstance(dish, str) and 0 < len(dish.strip()) <= 80 and any(c.isalpha() for c in dish):
        clean["dish"] = " ".join(dish.split())
    region = values.get("region")
    if isinstance(region, str):
        label = _REGION_CHOICES.get(region.strip().casefold())
        if label in CHINESE_REGIONS:
            clean["region"] = label
    return clean


def _response(reply, preferences, stage, *, options=(), results=(), ai_used=False):
    return {
        "reply": reply, "preferences": preferences, "stage": stage,
        "options": list(options), "results": list(results), "ai_used": ai_used,
    }


def discover_turn(message, previous, *, infer, recommend, online_city=None, chinese_regions=False):
    """Interpret a new answer, ask for a missing choice, or return grounded picks."""
    preferences = clean_preferences(previous)
    if not chinese_regions or preferences["cuisine"] != "Chinese":
        preferences.pop("region", None)
    exact = _EXACT_CHOICES.get(message.casefold())
    region_choice = _REGION_CHOICES.get(message.casefold()) if chinese_regions else None
    ai_used = False
    if exact:
        key, label = exact
        changes = {key: label}
    elif region_choice:
        changes = {"cuisine": "Chinese", "region": region_choice}
    elif message.casefold() in {"surprise me", "anything", "随便", "都可以"}:
        changes = {"cuisine": preferences["cuisine"] or "Any cuisine", "taste": "Any flavor"}
    else:
        try:
            changes = clean_preferences(infer(message, preferences, cuisines=CUISINES, tastes=TASTES))
            if chinese_regions and changes.get("region") and changes["cuisine"] in ("", "Chinese"):
                changes["cuisine"] = "Chinese"
            else:
                changes.pop("region", None)
            ai_used = True
        except (RuntimeError, ValueError, OSError):
            if online_city:
                raise
            stage = "taste" if preferences["cuisine"] or preferences["dish"] else "cuisine"
            options = TASTE_OPTIONS if stage == "taste" else CUISINE_OPTIONS
            return _response("Free-text AI is temporarily unavailable. You can still choose an option below.",
                             preferences, stage, options=options)

    if not any(changes.values()):
        stage = "taste" if preferences["cuisine"] or preferences["dish"] else "cuisine"
        options = TASTE_OPTIONS if stage == "taste" else CUISINE_OPTIONS
        return _response("Tell me a dish, cuisine, or flavor you’re in the mood for.",
                         preferences, stage, options=options, ai_used=ai_used)

    new_cuisine = changes.get("cuisine")
    if new_cuisine and new_cuisine not in ("Any cuisine", preferences["cuisine"]) and not changes.get("dish"):
        preferences["dish"] = ""
    preferences.update({key: value for key, value in changes.items() if value})
    cuisine, taste, dish = (preferences[key] for key in _KEYS)
    if cuisine != "Chinese" or region_choice == _ANY_CHINESE_STYLE:
        preferences.pop("region", None)
    region = preferences.get("region")
    if not cuisine and not dish:
        return _response("Any cuisine in mind? Pick one, or let me look across cuisines.", preferences,
                         "cuisine", options=CUISINE_OPTIONS, ai_used=ai_used)
    if not taste:
        if dish:
            reply = "Got it. What kind of flavor would you like?"
        elif cuisine == "Any cuisine":
            reply = "I’ll look across cuisines. What kind of flavor are you in the mood for?"
        else:
            subject = f"{region} cuisine" if region else cuisine
            reply = f"Sounds like {subject}. What kind of flavor are you in the mood for?"
        return _response(reply, preferences,
                         "taste", options=TASTE_OPTIONS, ai_used=ai_used)

    results = recommend(preferences)
    chinese_spicy = chinese_regions and cuisine == "Chinese" and taste == "Spicy"
    region_options = ()
    if (chinese_spicy or region) and not dish:
        region_options = tuple(label for label in CHINESE_REGIONS if label != region)
    if region:
        region_options = (*region_options, _ANY_CHINESE_STYLE)
    if results:
        source = f"online menu sources in {online_city}" if online_city else "Philadelphia reviews"
        count = "one dish" if len(results) == 1 else f"{len(results)} dishes"
        reply = f"I found {count} matching your picks in {source}."
        if chinese_spicy and len(results) > 1:
            reply += " Menus that describe the heat directly come first."
        if region_options:
            reply += " Try another Chinese style below." if region else " You can narrow by regional style below."
        options = region_options
        if not options and online_city and len(results) == 1 and taste != "Any flavor":
            reply += " Choose Any flavor to see more options with your other choices."
            options = ("Any flavor",)
        return _response(reply, preferences, "results", options=options, results=results, ai_used=ai_used)
    options = ([option for option in TASTE_OPTIONS if option != taste] if taste != "Any flavor" else
               [option for option in CUISINE_OPTIONS if option != cuisine])
    if taste != "Any flavor" and cuisine and cuisine != "Any cuisine":
        options.append("Any cuisine")
    reply = "I didn’t find a close match in our Philadelphia reviews. Try a different flavor, dish, or cuisine."
    if region:
        reply = f"I couldn’t verify a menu match for {region} and your other choices. Try Any Chinese style to widen the search."
        options = list(region_options)
    elif online_city:
        reply = "I couldn’t confirm a dish for these choices on the menus I checked."
        if "Any flavor" in options:
            options.remove("Any flavor")
            options.insert(0, "Any flavor")
            reply += " Choose Any flavor to keep your other choices and look again."
        else:
            reply += " Try a different dish or cuisine."
        if region_options:
            options = [*region_options, *options]
    return _response(reply, preferences, "results", options=options, ai_used=ai_used)


def _words(value):
    return re.findall(r"[^\W_]+", value.casefold())


def _dish_words(value):
    return {word.removesuffix("s") if len(word) > 3 else word for word in _words(value)}


def _taste_evidence(row, taste):
    terms = TASTE_TERMS[taste]
    try:
        tags = json.loads(row.taste_tags_clean)
    except (TypeError, ValueError):
        tags = []
    tags = {tag.casefold() for tag in tags if isinstance(tag, str)} if isinstance(tags, list) else set()
    name = " ".join(_words(row.dish_name_normalized))
    if taste == "Spicy" and (tags.intersection(TASTE_TERMS["Mild"]) or re.search(r"\b(?:not|non) spicy\b", name)):
        return ""
    for term in terms:
        if term in tags or f" {' '.join(_words(term))} " in f" {name} ":
            return term
    return ""


def review_matches(frame, preferences, sentiments, limit=3):
    """Choose real review pairs that have evidence for the selected preferences."""
    cuisine = CUISINE_GROUPS.get(preferences["cuisine"])
    taste = preferences["taste"]
    dish = " ".join(_words(preferences["dish"]))
    # The cuisine is already enforced by the restaurant group. Keep trailing
    # words such as the "Thai" in "pad Thai" as part of the dish name.
    prefix = f"{preferences['cuisine'].casefold()} "
    if cuisine and dish.startswith(prefix):
        dish = dish.removeprefix(prefix)
    dish_words = _dish_words(dish)
    labels = {group: label for label, group in CUISINE_GROUPS.items()}
    matches = []
    for row, sentiment in zip(frame.itertuples(index=False), sentiments):
        group = getattr(row, "cuisine_group", "")
        if cuisine and group != cuisine:
            continue
        if str(getattr(row, "historical_is_open", "")) in {"0", "0.0"} or row.positive_count <= 0:
            continue
        if dish_words and not dish_words.issubset(_dish_words(row.dish_name_normalized)):
            continue
        evidence = ""
        if taste in TASTE_TERMS:
            evidence = _taste_evidence(row, taste) if hasattr(row, "taste_tags_clean") else ""
            if not evidence:
                continue
        score = float(sentiment) + 0.12 * log1p(row.review_count)
        matches.append((score, row, labels.get(group, "") if cuisine else "", evidence))

    results, seen = [], set()
    for _, row, label, evidence in sorted(matches, key=lambda match: match[0], reverse=True):
        restaurant = row.restaurant_name
        if restaurant.casefold() in seen:
            continue
        seen.add(restaurant.casefold())
        results.append({
            "dish_name": row.dish_name_normalized.title(), "restaurant_name": restaurant,
            "review_count": int(row.review_count), "cuisine": label, "taste_match": evidence,
        })
        if len(results) >= limit:
            break
    return results
