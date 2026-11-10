"""Retrieve public menus for Discover and verify the model's recommendations."""

from __future__ import annotations

from html import unescape
import os
import re
from unicodedata import normalize
from urllib.parse import unquote, urldefrag, urlsplit

import requests

from discover_chat import TASTE_TERMS
from discover_gemini import GeminiDiscoverError
from discover_online import _public_url, _text


_SEARCH_URL = "https://api.tavily.com/search"
_SEARCH_LIMIT = 8
_MODEL_SOURCE_LIMIT = 6
_FOLLOWUP_SOURCE_LIMIT = 4
_EXCERPT_LIMIT = 1760
_CARD_LIMIT = 3
_EXCLUDED_DOMAINS = ("facebook.com", "instagram.com", "reddit.com", "tiktok.com", "tripadvisor.com", "yelp.com")
_ORDERING_DOMAINS = ("opentable.com", "toasttab.com")
_FLEXIBLE = {"any cuisine", "any flavor"}
_REGION_ALIASES = {
    "Sichuan": ("Sichuan", "Szechuan", "Szechwan"),
    "Hunan": ("Hunan",),
    "Cantonese": ("Cantonese",),
}
_FOLLOWUP_DISH_TERMS = {
    ("Italian", "Crispy"): ("fried calamari", "arancini", "fritto misto", "chicken Milanese"),
    ("Japanese", "Crispy"): ("tempura", "karaage", "katsu"),
    ("Korean", "Crispy"): ("Korean fried chicken", "fried mandu", "crispy pancakes"),
    ("Thai", "Spicy"): ("drunken noodles", "green curry", "Thai chili"),
    ("Chinese", "Spicy"): ("chili oil wontons", "fish with chopped chiles", "spicy dry pot"),
    ("Sichuan", "Spicy"): ("Sichuan spicy eggplant", "Szechuan peppercorn"),
    ("Hunan", "Spicy"): ("Hunan spicy beef", "Hunan spicy fish"),
    ("Mexican", "Fresh & light"): ("ceviche", "citrus salsa", "grilled fish tacos"),
}
_FOLLOWUP_TASTE_TERMS = {
    "Crispy": ("breaded", "crunchy", "deep fried"),
    "Spicy": ("chili", "hot sauce", "peppery"),
    "Fresh & light": ("fresh herbs", "citrus", "light broth"),
    "Rich & creamy": ("cream sauce", "velvety", "buttery"),
    "Sweet": ("sweet glaze", "caramelized", "dessert"),
}
_CRISPY_EVIDENCE = re.compile(
    r"\b(?:crispy|crisp|crunchy|crunchiness|breaded|battered|panko|fritto|fritti|tempura|"
    r"deep fried|fried (?:calamari|chicken|shrimp|fish|mozzarella|spring rolls?|onion rings|(?:rice|risotto) balls?))\b"
)
_DIRECT_HEAT = re.compile(r"\b(?:spicy|spicey|spiciness|fiery|mala|ma la|hot and numbing)\b")
_PREPARATION_HEAT = re.compile(
    r"\b(?:"
    r"hot (?:chil(?:i|li|e)(?:es|s)?|peppers?|sauce|bean paste)|"
    r"chil(?:i|li|e) (?:oil|crisp|peppers?|flakes?)|"
    r"(?:dried|crushed|chopped) (?:red )?chil(?:i|li|e)(?:es|s)?|"
    r"(?:sichuan|szechuan|szechwan) peppercorns?)\b"
)
_SPICY_PREPARATION = re.compile(
    r"\b(?:spicy|fiery|mala|ma la|hot and spicy|hot and numbing) "
    r"(?:\w+ ){0,3}(?:sauce|broth|oil|glaze|marinade|paste|seasoning|rub)\b"
)
_MILD_EVIDENCE = re.compile(
    r"\b(?:mild|mildly|(?:not|non|never) (?:(?:too|very|overly|really|at all) )?spicy|not hot|"
    r"(?:no|without) (?:added )?(?:heat|spice|chil(?:i|li|e)(?:es|s)?))\b"
)
_PRICE_LINE = re.compile(r"(?:#{1,6}\s+|\*\*)?\$?\d+(?:[.,]\d{1,2})?\+?(?:\*\*)?$")
_ITEM_START = re.compile(r"^(?:#{1,6}\s|[-*+]\s|\[?\*\*[^\n]+\*\*)")
_ITEM_PRICE_SUFFIX = re.compile(
    r"\s+(?:\([A-Z]{1,3}\)\s*)?\$?\d{1,3}\.\d{2}"
    r"(?:\s*[-–—]\s*(?:\([A-Z]{1,3}\)\s*)?\$?\d{1,3}\.\d{2})?$"
)
_MENU_SECTION = re.compile(
    r"^#{1,6}\s+(?:appetizers|starters|entrées|entrees|main dishes|desserts|antipasti|primi|secondi)\b",
    re.I | re.M,
)
_MENU_PRICE = re.compile(r"\$\s*\d+\.\d{2}\b")


class TavilyDiscoverError(RuntimeError):
    """A menu search failure with a message safe to show in Discover."""


def tavily_configured():
    return bool(os.environ.get("TAVILY_API_KEY", "").strip())


def _fetch_results(query, *, read_timeout=25):
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        raise TavilyDiscoverError("Online menu search needs a Tavily API key in the local server environment.")
    try:
        response = requests.post(
            _SEARCH_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "query": query,
                "topic": "general",
                "search_depth": "advanced",
                "chunks_per_source": 3,
                "max_results": _SEARCH_LIMIT,
                "include_raw_content": "markdown",
                "include_answer": False,
                "exclude_domains": list(_EXCLUDED_DOMAINS),
            },
            timeout=(5, read_timeout),
            allow_redirects=False,
        )
    except requests.Timeout:
        raise TavilyDiscoverError("Online menu search took too long. Try again in a moment.") from None
    except requests.RequestException:
        raise TavilyDiscoverError("Discover could not reach Tavily's menu search.") from None

    if response.status_code in (401, 403):
        raise TavilyDiscoverError("Tavily did not authorize the local server. Check its API key.")
    if response.status_code in (402, 432, 433):
        raise TavilyDiscoverError("Tavily reached its search credit limit.")
    if response.status_code in (429, 434):
        raise TavilyDiscoverError("Tavily reached a search limit. Try again in a moment.")
    if response.status_code != 200:
        raise TavilyDiscoverError("Tavily could not complete the menu search.")
    try:
        results = response.json().get("results")
    except (AttributeError, ValueError):
        results = None
    if not isinstance(results, list):
        raise TavilyDiscoverError("Tavily returned an incomplete menu search response.")
    return results[:_SEARCH_LIMIT]


def _normalized(value):
    value = normalize("NFKC", unescape(value)).casefold().replace("&", " and ")
    return " ".join(re.findall(r"[^\W_]+", value))


def _contains(phrase, text):
    words = _normalized(phrase)
    return bool(words and f" {words} " in f" {_normalized(text)} ")


def _chinese_region(preferences):
    region = _text(preferences.get("region"), 30)
    return region if preferences.get("cuisine") == "Chinese" and region in _REGION_ALIASES else ""


def _restaurant_key(name):
    return _normalized(name.replace("'", "").replace("’", ""))


def _menu_key(value):
    url = _public_url(value)
    if not url:
        return ()
    parsed = urlsplit(url)
    return (parsed.hostname.removeprefix("www."), parsed.path.rstrip("/"), parsed.query)


def _visible_text(value, limit):
    if not isinstance(value, str):
        return ""
    value = re.sub(r"!\[[^\]\n]*\]\([^\n]*?\)", "", value[:limit])
    return re.sub(r"\[([^\]\n]+)\]\([^\n]*?\)", r"\1", value).strip()


def _looks_like_menu(page_label, hostname, raw, snippets):
    if any(_contains(label, page_label) for label in ("menu", "menus", "order online")):
        return True
    if _MENU_SECTION.search(raw) and any(_contains(label, f"{page_label} {raw}")
                                         for label in ("menu", "dinner", "lunch", "brunch")):
        return True
    # Some ordering and reservation pages expose actual menu items only in the search excerpt.
    ordering_page = _contains("order", page_label) or any(
        hostname == domain or hostname.endswith(f".{domain}") for domain in _ORDERING_DOMAINS
    )
    return ordering_page and len(_MENU_PRICE.findall(snippets or raw)) >= 2


def _focused_passage(value, limit, terms):
    if len(value) <= limit:
        return value.strip()
    start = 0
    for term in terms:
        match = re.search(rf"(?<!\w){re.escape(term)}(?!\w)", value, re.I)
        if match:
            start = max(0, min(match.start() - limit // 3, len(value) - limit))
            break
    return value[start:start + limit].strip()


def _menu_passages(raw, snippets, page_label, city, terms):
    chunks = [part.strip() for part in re.split(r"\[\s*\.\.\.\s*\]", snippets) if part.strip()][:3]
    chunks.sort(key=lambda part: any(_contains(term, part) for term in terms), reverse=True)
    passages = [_focused_passage(part, 560, terms) for part in chunks[:2]]

    heading = re.search(r"^#\s+([^\n]+)$", raw[:2500], re.M)
    header = _text(heading[1], 180) if heading else raw[:230].strip()
    if header and not _contains(header, f"{page_label} {' '.join(passages)}"):
        passages.insert(0, header)

    if not _contains(city, f"{page_label} {' '.join(passages)}"):
        nearby = next((part for part in [*chunks, *raw.splitlines()] if _contains(city, part)), "")
        if nearby:
            passages.insert(0, _focused_passage(nearby, 170, (city,)))

    remaining = _EXCERPT_LIMIT - sum(len(part) + 2 for part in passages)
    if raw and remaining >= 160:
        details = _focused_passage(raw, remaining, terms)
        if details and not any(_contains(details, part) for part in passages):
            passages.append(details)
    return passages


def _menu_sources(pages, city, preferences=None, *, limit=_MODEL_SOURCE_LIMIT):
    sources = []
    evidence = {}
    seen = set()
    preferences = preferences or {}
    dish = _text(preferences.get("dish"), 80)
    cuisine = preferences.get("cuisine")
    taste = preferences.get("taste")
    terms = tuple(term for term in (dish, *_REGION_ALIASES.get(_chinese_region(preferences), ()),
                                    *TASTE_TERMS.get(taste, ()),
                                    *_FOLLOWUP_DISH_TERMS.get((cuisine, taste), ()),
                                    *_FOLLOWUP_TASTE_TERMS.get(taste, ())) if term)
    for page in pages:
        if not isinstance(page, dict):
            continue
        url = _public_url(page.get("url"))
        if not url or urldefrag(url).url in seen:
            continue
        parsed = urlsplit(url)
        hostname = parsed.hostname or ""
        if any(hostname == domain or hostname.endswith(f".{domain}") for domain in _EXCLUDED_DOMAINS):
            continue

        title = _text(page.get("title"), 160) or hostname
        page_label = f"{title} {unquote(parsed.path)}"
        raw = _visible_text(page.get("raw_content"), 80_000)
        snippets = _visible_text(page.get("content"), 4000)
        if not raw and not snippets:
            continue

        if not _looks_like_menu(page_label, hostname, raw, snippets):
            continue

        passages = _menu_passages(raw, snippets, page_label, city, terms)
        location_text = f"{page_label} {' '.join(passages)}"
        if not _contains(city, location_text):
            continue

        seen.add(urldefrag(url).url)
        source_id = len(sources) + 1
        sources.append({"id": source_id, "title": title, "url": url, "excerpt": "\n\n".join(passages)})
        evidence[source_id] = (passages, location_text)
        if len(sources) == limit:
            break
    return sources, evidence


def _priced_item_title(line):
    match = _ITEM_PRICE_SUFFIX.search(line)
    title = line[:match.start()] if match else ""
    return title if any(char.isalpha() for char in title) else ""


def _item_title_matches(title, dish):
    if _ITEM_START.match(title):
        return _contains(dish, title)
    return _normalized(_priced_item_title(title)) == _normalized(dish)


def _menu_items(passage, *, priced_titles=False):
    lines = []
    for line in passage.splitlines():
        heading = line.strip()
        marked = _ITEM_START.match(heading) and not _PRICE_LINE.fullmatch(heading)
        if lines and (marked or (priced_titles and _priced_item_title(heading))):
            yield "\n".join(lines)
            lines = []
        lines.append(line)
    if lines:
        yield "\n".join(lines)


def _supported_note(quote, dish, passages, restaurant="", *, heat=False):
    quote = _text(quote, 180)
    if not quote:
        return ""
    dish_words, quote_words = _normalized(dish), _normalized(quote)
    if not quote_words:
        return ""
    if _contains(quote, dish):
        if _contains(quote, restaurant):
            return ""
        if not heat:
            return quote if any(_contains(dish, passage) for passage in passages) else ""
    for passage in passages:
        # A heading or list marker can start a new menu item. Never borrow its description.
        for item in _menu_items(passage):
            text = f" {_normalized(item)} "
            names = [match.start() for match in re.finditer(re.escape(f" {dish_words} "), text)]
            notes = [match.start() for match in re.finditer(re.escape(f" {quote_words} "), text)]
            if heat:
                # The word "spicy" can be quoted from a sentence that actually says "not spicy".
                notes = [start for start in notes if not _MILD_EVIDENCE.search(
                    text[max(0, start - 24):start + len(quote_words) + 24]
                )]
            if any(abs(name - note) <= 240 for name in names for note in notes):
                return quote
    return ""


def _regional_match(region, quote, dish, passages, restaurant, source_title):
    aliases = _REGION_ALIASES[region]
    if any(_contains(alias, dish) and _normalized(alias) != _normalized(dish) for alias in aliases):
        return "dish"
    quote = _text(quote, 180)
    if any(_contains(alias, quote) for alias in aliases):
        for passage in passages:
            for item in _menu_items(passage, priced_titles=True):
                title = item.partition("\n")[0].strip()
                # A flattened excerpt can put the names of two dishes next to each other.
                if _item_title_matches(title, dish):
                    if _supported_note(quote, dish, [item], restaurant):
                        return "dish"

    declarations = tuple(f"{alias} {kind}" for alias in aliases for kind in ("cuisine", "cooking", "menu"))
    if _contains(restaurant, source_title) and any(_contains(label, source_title) for label in declarations):
        return "menu"
    if any(_contains(label, quote) for label in declarations):
        for passage in passages:
            for line in passage.splitlines():
                if _contains(quote, line) and _contains(restaurant, line):
                    return "menu"
    return ""


def _heat_cue(value):
    words = _normalized(value)
    return _DIRECT_HEAT.search(words) or _PREPARATION_HEAT.search(words)


def _explicit_heat(card):
    return bool(_DIRECT_HEAT.search(_normalized(card["note"])))


def _has_heat_detail(value, dish):
    words = _normalized(value)
    return not _contains(value, dish) and bool(_PREPARATION_HEAT.search(words) or _SPICY_PREPARATION.search(words))


def _spicy_detail(quote, dish, passages, restaurant):
    """Find a preparation detail only inside a clearly bounded menu item."""
    for passage in passages:
        for item in _menu_items(passage, priced_titles=True):
            title, _, description = item.partition("\n")
            if not _item_title_matches(title.strip(), dish):
                continue
            for line in description.splitlines():
                detail = " ".join(line.split())
                if len(detail) <= 140 and _has_heat_detail(detail, dish):
                    if _supported_note(detail, dish, [item], restaurant, heat=True):
                        return detail
            if _has_heat_detail(quote, dish) and _supported_note(quote, dish, [item], restaurant, heat=True):
                return quote
    return ""


def _pick_results(pages, preferences, city, select_picks, existing=(), *,
                  source_limit=_MODEL_SOURCE_LIMIT, excluded=()):
    city_name = city.partition(",")[0].strip()
    chosen_cuisine = _text(preferences.get("cuisine"), 80)
    taste = _text(preferences.get("taste"), 80)
    region = _chinese_region(preferences)
    chinese_spicy = chosen_cuisine == "Chinese" and taste == "Spicy"
    has_taste = bool(taste and taste.casefold() not in _FLEXIBLE)
    if excluded:
        # Search titles can mention several venues, so only deprioritize likely repeats here.
        def shown_menu(page):
            if not isinstance(page, dict):
                return False
            title = f" {_restaurant_key(_text(page.get('title'), 160))} "
            return any(f" {restaurant} " in title for restaurant in excluded)

        pages = sorted(pages, key=shown_menu)
    sources, evidence = _menu_sources(pages, city_name, preferences, limit=source_limit)
    if not sources:
        return []

    indexed = {source["id"]: source for source in sources}
    picks = select_picks(preferences, city, sources)
    if not isinstance(picks, list):
        return []

    results = []
    restaurants = set(excluded)
    restaurants.update(_restaurant_key(item["restaurant_name"]) for item in existing)
    menu_urls = {_menu_key(item["source_url"]) for item in existing}
    for pick in picks:
        if not isinstance(pick, dict) or type(pick.get("source_id")) is not int:
            continue
        source = indexed.get(pick["source_id"])
        if not source or _menu_key(source["url"]) in menu_urls:
            continue
        dish = _text(pick.get("dish_name"), 100)
        restaurant = _text(pick.get("restaurant_name"), 120)
        brand = _restaurant_key(restaurant)
        passages, location_text = evidence[source["id"]]
        if (not brand or brand in restaurants or brand == _normalized(dish)
                or not any(_contains(dish, passage) for passage in passages)
                or not _contains(restaurant, location_text)):
            continue

        cuisine = _text(pick.get("cuisine"), 60)
        if (region or chinese_spicy) and _normalized(cuisine) != "chinese":
            continue
        if chosen_cuisine and chosen_cuisine.casefold() not in _FLEXIBLE and cuisine:
            if _normalized(cuisine) != _normalized(chosen_cuisine):
                continue
        region_scope = ""
        if region:
            region_scope = _regional_match(region, pick.get("region_evidence"), dish, passages, restaurant, source["title"])
            if not region_scope:
                continue
        location = _text(pick.get("location"), 120)
        quote = _supported_note(pick.get("taste_evidence"), dish, passages, restaurant, heat=chinese_spicy)
        if taste == "Crispy" and not _CRISPY_EVIDENCE.search(_normalized(quote)):
            # The menu name itself can establish a crispy preparation, such as Fried Calamari.
            quote = dish if _CRISPY_EVIDENCE.search(_normalized(dish)) else ""
        if chinese_spicy:
            dish_words, quote_words = _normalized(dish), _normalized(quote)
            if _MILD_EVIDENCE.search(dish_words) or _MILD_EVIDENCE.search(quote_words):
                continue
            detail = _spicy_detail(quote, dish, passages, restaurant)
            partial_title = quote_words != dish_words and _contains(quote, dish)
            short_label = len(quote_words.split()) <= 3 and not _has_heat_detail(quote, dish)
            stronger_title = _DIRECT_HEAT.search(dish_words) and (
                short_label or not _DIRECT_HEAT.search(quote_words)
            )
            if partial_title or not _heat_cue(quote) or stronger_title:
                name_quote = _supported_note(dish, dish, passages, restaurant, heat=True)
                if _heat_cue(name_quote):
                    quote = name_quote
            if detail and (not _DIRECT_HEAT.search(_normalized(quote)) or _DIRECT_HEAT.search(_normalized(detail))):
                quote = detail
            if not _heat_cue(quote):
                continue
        if has_taste and not quote:
            continue
        result = {
            "dish_name": dish,
            "restaurant_name": restaurant,
            "cuisine": cuisine if region or _contains(cuisine, location_text) else "",
            "location": location if _contains(city_name, location) and _contains(location, location_text) else city_name,
            "source_url": source["url"],
            "source_title": source["title"],
            "note": f"Menu mentions “{quote}”" if quote else "",
        }
        if region_scope:
            result["region" if region_scope == "dish" else "menu_region"] = region
        if chinese_spicy and detail:
            result["why"] = f"For your spicy pick, the menu says “{detail.rstrip('.')}”."
        results.append(result)

    if chinese_spicy:
        results.sort(key=_explicit_heat, reverse=True)
    distinct = []
    for result in results:
        brand = _restaurant_key(result["restaurant_name"])
        menu = _menu_key(result["source_url"])
        if brand in restaurants or menu in menu_urls:
            continue
        restaurants.add(brand)
        menu_urls.add(menu)
        distinct.append(result)
        if len(distinct) + len(existing) == _CARD_LIMIT:
            break
    return distinct


def _followup_pages(pages, initial_pages, cards):
    menus = {_menu_key(card["source_url"]) for card in cards}
    restaurants = {_restaurant_key(card["restaurant_name"]) for card in cards}
    earlier = {_menu_key(page.get("url")): page.get("content") for page in initial_pages if isinstance(page, dict)}
    remaining = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        menu = _menu_key(page.get("url"))
        if not menu or menu in menus or (menu in earlier and page.get("content") == earlier[menu]):
            continue
        title = re.split(r"\s+[|–—-]\s+", _text(page.get("title"), 160), maxsplit=1)[0]
        name = _restaurant_key(title)
        if name in restaurants or name.removesuffix(" menu") in restaurants or name.removesuffix(" menus") in restaurants:
            continue
        remaining.append(page)
    remaining.sort(key=lambda page: _menu_key(page.get("url")) in earlier)
    return remaining


def search_tavily(preferences, city, *, select_picks, exclude_restaurants=()):
    """Return up to three distinct, menu-backed restaurants beyond any already shown."""
    city = _text(city, 100)
    cuisine, taste, dish = (_text(preferences.get(field), 80) for field in ("cuisine", "taste", "dish"))
    region = _chinese_region(preferences)
    excluded = {_restaurant_key(_text(name, 120)) for name in exclude_restaurants}
    excluded.discard("")
    choices = [value for value in (cuisine, region, taste, dish) if value and value.casefold() not in _FLEXIBLE]
    query = " ".join([city, "restaurant menus", *choices])
    if region:
        regional_choices = [value for value in (taste, dish) if value and value.casefold() not in _FLEXIBLE]
        query = " ".join([city, region, "cuisine restaurant menus", *regional_choices])
    pages = _fetch_results(query)
    cards = _pick_results(pages, preferences, city, select_picks, excluded=excluded)
    if len(cards) == _CARD_LIMIT:
        return cards

    related = () if dish else _FOLLOWUP_DISH_TERMS.get((region or cuisine, taste), ())
    terms = related or _FOLLOWUP_TASTE_TERMS.get(taste, ())
    if excluded:
        followup_query = " ".join([city, *choices, "takeout menus order online"])
    elif region and not cards:
        # A narrow query can miss Chinese menus whose regional style is listed on individual dishes.
        broader_choices = [value for value in (cuisine, taste, dish) if value and value.casefold() not in _FLEXIBLE]
        followup_query = " ".join([city, "restaurant menus", *broader_choices])
    elif region and terms:
        followup_query = f"{query} with {' or '.join(terms[:2])}"
    elif terms:
        # Substitute menu vocabulary for the abstract taste label to find different sources.
        menu_type = " ".join(value for value in (cuisine, dish) if value and value.casefold() not in _FLEXIBLE)
        followup_query = f"{city} {menu_type} restaurant dinner menus with {' or '.join(terms[:2])}"
    else:
        followup_query = f"{query} with dinner dishes and restaurant ordering pages"
    try:
        more_pages = _fetch_results(followup_query, read_timeout=12)
        fresh_pages = _followup_pages(more_pages, pages, cards)
        cards.extend(_pick_results(fresh_pages, preferences, city, select_picks, cards,
                                   source_limit=_FOLLOWUP_SOURCE_LIMIT, excluded=excluded))
    except (TavilyDiscoverError, GeminiDiscoverError):
        if not cards:
            raise
    if cuisine == "Chinese" and taste == "Spicy":
        cards.sort(key=_explicit_heat, reverse=True)
    return cards
