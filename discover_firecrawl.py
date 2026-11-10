"""Find live menu pages for Discover and verify the local model's picks."""

from __future__ import annotations

import os
import re
from urllib.parse import unquote, urljoin, urlsplit

import requests

from discover_chat import TASTE_TERMS
from discover_online import _public_url, _text


_API_URL = "https://api.firecrawl.dev/v2"
_SEARCH_LIMIT = 6
_RESULT_LIMIT = 3
_EXCERPT_LIMIT = 2350
_FLEXIBLE = {"any cuisine", "any flavor"}
_LOCATION_PATHS = {"/location", "/locations", "/contact", "/contact-us"}
_CUISINE_SIGNALS = {
    "Japanese": ("sushi", "ramen", "udon", "sashimi", "nigiri", "tempura", "yakitori"),
    "Italian": ("pizzeria", "pizza", "pasta", "risotto", "spaghetti", "lasagna", "gnocchi"),
    "Mexican": ("taqueria", "tacos", "taco", "burrito", "enchiladas", "enchilada"),
    "Thai": ("pad thai", "pad see ew", "tom yum", "tom kha", "panang", "massaman"),
    "Chinese": ("sichuan", "szechuan", "dim sum", "mapo tofu", "kung pao", "chow mein"),
    "Korean": ("bibimbap", "bulgogi", "kimchi", "tteokbokki", "kimbap", "gimbap"),
}
_SPICY_SIGNALS = ("chili oil", "chile oil", "hot sauce", "jalapeño", "jalapeno")
_MAIN_ITEM_WORDS = {
    "bowl", "burger", "burrito", "curry", "donburi", "entrée", "entree", "gnocchi", "lasagna",
    "noodles", "pasta", "pizza", "platter", "ramen", "risotto", "sandwich", "spaghetti",
    "sushi", "taco", "tacos", "udon",
}
_ITEM_PRICE = re.compile(r"(?:^\s*\$\s*\d|\b(?:dine[- ]in|pickup)\s+\$?\d)", re.I | re.M)
_ITEM_DESCRIPTION = re.compile(r"\b(?:served with|topped with|made with|battered|fried|grilled|roasted|broth|sauce)\b", re.I)
_PRICE_NUMBER = r"\$?\s*\d+(?:\.\d{1,2})?\+?"
_INLINE_HEADING_PRICE = re.compile(rf"\s*\\?\|\s*({_PRICE_NUMBER})\s*$")
_CURRENCY_LINE = re.compile(r"^\$\s*\d+(?:\.\d{1,2})?\+?$")
_BOLD_ITEM = re.compile(r"^\[?\*\*(.{2,100})\*\*$")
_ORIGINAL_PRICE = re.compile(r"^Original price was (\$\d+(?:\.\d{1,2})?)$", re.I)


class FirecrawlDiscoverError(RuntimeError):
    """A menu search failure with a message suitable for the chat UI."""


def _words(value):
    return " ".join(re.findall(r"[^\W_]+", value.casefold()))


def _contains(phrase, evidence):
    normalized = _words(phrase)
    return bool(normalized and f" {normalized} " in f" {_words(evidence)} ")


def _search_terms(preferences):
    choices = []
    for field in ("cuisine", "taste", "dish"):
        value = _text(preferences.get(field), 80)
        if value and value.casefold() not in _FLEXIBLE:
            choices.append(value)
    return choices


def _firecrawl_post(endpoint, payload, timeout):
    key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        response = requests.post(
            f"{_API_URL}/{endpoint}",
            headers=headers,
            json=payload,
            timeout=(5, timeout),
            allow_redirects=False,
        )
    except requests.Timeout:
        raise FirecrawlDiscoverError("Online menu search took too long. Try again in a moment.") from None
    except requests.RequestException:
        raise FirecrawlDiscoverError("Discover could not reach the online menu search.") from None

    if response.status_code == 429:
        message = ("Online menu search reached its request limit. Try again later." if key else
                   "Free online menu search reached its request limit. Try again later.")
        raise FirecrawlDiscoverError(message)
    if response.status_code == 402:
        raise FirecrawlDiscoverError("Online menu search is out of credits for the current access plan.")
    if response.status_code in (401, 403):
        raise FirecrawlDiscoverError("Firecrawl denied access. Check the local server’s search configuration.")
    if response.status_code != 200:
        raise FirecrawlDiscoverError("Online menu search could not complete. Try again in a moment.")
    try:
        body = response.json()
        if body.get("success") and "data" in body:
            return body["data"]
    except (AttributeError, ValueError):
        pass
    raise FirecrawlDiscoverError("Online menu search returned an incomplete response. Try again.")


def _fetch_menus(city, preferences):
    choices = _search_terms(preferences)
    cuisine = _text(preferences.get("cuisine"), 80)
    leading = choices[:1] if choices and choices[0] == cuisine else []
    query = " ".join((city, *leading, "restaurant menu", *choices[len(leading):]))
    data = _firecrawl_post("search", {
        "query": query,
        "limit": _SEARCH_LIMIT,
        "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True},
    }, timeout=30)
    results = data.get("web") if isinstance(data, dict) else data
    if not isinstance(results, list):
        raise FirecrawlDiscoverError("Online menu search returned an incomplete response. Try again.")
    return results[:_SEARCH_LIMIT]


def _without_markdown_links(markdown):
    markdown = re.sub(r"!\[[^\]\n]*\]\([^\n]*?\)", "", markdown)
    return re.sub(r"\[([^\]\n]+)\]\([^\n]*?\)", r"\1", markdown)


def _menu_heading_blocks(lines):
    headings = [(index, match) for index, line in enumerate(lines)
                if (match := re.fullmatch(r"(#{1,6})\s+(.+)", line))]
    for position, (start, heading) in enumerate(headings):
        title = heading[2].replace("**", "").strip()
        if re.fullmatch(_PRICE_NUMBER, title):
            continue
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        body = lines[start + 1:min(end, start + 3)]
        inline_price = _INLINE_HEADING_PRICE.search(title)
        price = inline_price[1] if inline_price else ""
        if inline_price:
            title = title[:inline_price.start()].strip()
        if position + 1 < len(headings):
            deeper = headings[position + 1][1]
            if len(deeper[1]) > len(heading[1]):
                if inline_price:
                    body = [deeper[2]] + body
                elif re.fullmatch(_PRICE_NUMBER, deeper[2]):
                    price = deeper[2]
                    next_end = headings[position + 2][0] if position + 2 < len(headings) else len(lines)
                    body = lines[end + 1:min(next_end, end + 3)]
        if 2 <= len(title) <= 100 and (body or price):
            content = [f"{heading[1]} {title}", *body]
            if price:
                content.append(f"${price.strip().lstrip('$')}")
            yield title, "\n".join(content)[:500]


def _priced_menu_blocks(lines, *, allow_plain_prices=False):
    # Bare prices alone cannot identify items in reviews or page navigation.
    # Recognize explicit bullet/bold items and the ordering site's price label.
    lines = [cleaned for line in lines if (cleaned := line.rstrip("\\").strip())]
    for index, line in enumerate(lines):
        bold = _BOLD_ITEM.fullmatch(line)
        title = line[2:].strip("*") if line.startswith("- ") else bold[1] if bold else ""
        if 2 <= len(title) <= 100 and not _CURRENCY_LINE.fullmatch(title):
            body = []
            for following in lines[index + 1:index + 6]:
                price = following.strip("*").strip()
                if _CURRENCY_LINE.fullmatch(price):
                    yield title, "\n".join([f"### {title}", *body, price])[:500]
                    break
                if following.startswith(("#", "- ")) or _BOLD_ITEM.fullmatch(following):
                    break
                body.append(following)

        price = _ORIGINAL_PRICE.fullmatch(line) if allow_plain_prices else None
        if not price or index < 1:
            continue
        previous = lines[index - 1]
        description = previous if previous.endswith((".", "!")) or "," in previous else ""
        title_index = index - 2 if description else index - 1
        if title_index < 0:
            continue
        title = lines[title_index]
        if (2 <= len(title) <= 100 and not title.startswith(("#", "- ", "[", "$"))
                and not re.search(r"\bprice\s+(?:was|is)\b", title, re.I)):
            body = [description] if description else []
            yield title, "\n".join([f"### {title}", *body, price[1]])[:500]


def _item_priority(dish, taste):
    words = set(_words(dish).split())
    main = bool(_MAIN_ITEM_WORDS.intersection(words) and not words.intersection({"small", "side", "appetizer"}))
    direct_taste = any(_contains(term, dish) for term in TASTE_TERMS.get(taste, ()))
    return main, direct_taste


def _item_evidence(block):
    return bool(_ITEM_PRICE.search(block) or _ITEM_DESCRIPTION.search(block.partition("\n")[2]))


def _menu_excerpt(markdown, preferences, city, *, allow_plain_prices=False):
    # Preserve labels and dish names while removing long Markdown URLs and images.
    markdown = _without_markdown_links(markdown)
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    if not lines:
        return ""
    excerpt = "\n".join(lines)[:_EXCERPT_LIMIT]
    weighted_terms = {}
    for field, weight in (("cuisine", 1), ("taste", 3), ("dish", 5)):
        value = _text(preferences.get(field), 80)
        if value.casefold() not in _FLEXIBLE:
            for term in set(_words(value).split()) - {"and", "with", "a", "the"}:
                weighted_terms[term] = weight
    dish_words = set(_words(_text(preferences.get("dish"), 80)).split())
    taste = _text(preferences.get("taste"), 60)
    focused = []
    if dish_words or taste:
        blocks = [*_menu_heading_blocks(lines), *_priced_menu_blocks(lines, allow_plain_prices=allow_plain_prices)]
        for title, block in blocks:
            if dish_words and not dish_words.issubset(_words(title).split()):
                continue
            if not dish_words and not _item_evidence(block):
                continue
            if taste in TASTE_TERMS and not _taste_match(taste, title, block):
                continue
            focused.append((_item_priority(title, taste), block))
    if focused:
        focused.sort(key=lambda candidate: candidate[0], reverse=True)
        address = next((line[:130] for line in lines if _contains(city, line)), "")
        heading = next((line[:130] for line in lines[:50] if line.startswith("# ")), "")
        return "\n\n".join([line for line in (heading, address) if line] +
                          [block for _, block in focused[:4]])[:_EXCERPT_LIMIT]
    if not weighted_terms or len(markdown) <= _EXCERPT_LIMIT:
        return excerpt

    def relevance(index):
        nearby = " ".join(lines[max(0, index - 1):index + 2])
        words = set(_words(nearby).split())
        return sum(weighted_terms.get(word, 0) for word in words)

    # Include the page heading, then keep nearby menu lines around relevant hits.
    selected = ["\n".join(lines)[:650]]
    used = set()
    matches = sorted(range(len(lines)), key=relevance, reverse=True)
    for index in matches:
        if len(selected) >= 4 or relevance(index) == 0:
            break
        window = range(max(0, index - 2), min(len(lines), index + 4))
        if used.intersection(window):
            continue
        used.update(window)
        snippet = "\n".join(lines[i] for i in window)[:500]
        if snippet and snippet not in selected[0]:
            selected.append(snippet)
    if not _contains(city, "\n".join(selected)):
        address = next((line[:130] for line in lines if _contains(city, line)), "")
        if address:
            selected.insert(1, address)
    return "\n\n".join(selected)[:_EXCERPT_LIMIT] if len(selected) > 1 else excerpt


def _location_link(markdown, menu_url):
    menu_host = urlsplit(menu_url).hostname
    for target in re.findall(r"\[[^\]\n]+\]\(([^\s)]+)", markdown):
        try:
            url = _public_url(urljoin(menu_url, target))
        except ValueError:
            continue
        if not url:
            continue
        parsed = urlsplit(url)
        if (parsed.hostname == menu_host and not parsed.query and not parsed.fragment
                and parsed.path.rstrip("/").casefold() in _LOCATION_PATHS):
            return url
    return ""


def _location_evidence(url, city):
    page = _firecrawl_post("scrape", {"url": url, "formats": ["markdown"], "onlyMainContent": True}, timeout=12)
    if not isinstance(page, dict) or not isinstance(page.get("markdown"), str):
        return ""
    metadata = page.get("metadata")
    if isinstance(metadata, dict):
        final_url = metadata.get("url") or metadata.get("sourceURL") or url
        if not _public_url(final_url) or urlsplit(final_url).hostname != urlsplit(url).hostname:
            return ""
        if str(metadata.get("statusCode", 200)) != "200":
            return ""
    lines = _without_markdown_links(page["markdown"][:60_000]).splitlines()
    return next((_text(line, 180) for line in lines if _contains(city, line)), "")


def _ordering_menu_restaurant(title, url, markdown):
    parsed = urlsplit(url)
    if parsed.hostname in {"slicelife.com", "www.slicelife.com"} and parsed.path.startswith("/restaurants/"):
        name, divider, label = title.partition(" - ")
        if divider and _contains("menu", label) and _contains(name, unquote(parsed.path)):
            return name
    if parsed.hostname not in {"grubhub.com", "www.grubhub.com"} or not parsed.path.startswith("/restaurant/"):
        return ""
    heading = re.search(r"^#\s+([^\n]+)$", _without_markdown_links(markdown[:6000]), re.M)
    if heading and f"{_words(title)} ".startswith(f"{_words(heading[1])} "):
        return _text(heading[1], 120)
    return ""


def _official_menu_restaurant(title, metadata, url, markdown):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").removeprefix("www.").split(".", 1)[0]
    host_name = _words(host).replace(" ", "")
    name = _text(metadata.get("og:site_name") or metadata.get("ogSiteName"), 120)
    name = name.partition("|")[0].strip()
    if name and _contains(name, title) and _words(name).replace(" ", "") == host_name:
        return name
    heading = re.search(r"^#\s+([^\n]+)$", _without_markdown_links(markdown[:6000]), re.M)
    if heading and "/order-online" in parsed.path:
        words = _words(heading[1]).split()
        compact = words[0] + "".join(word[0] for word in words[1:]) if words else ""
        path_words = set(_words(unquote(parsed.path)).split())
        if compact == host_name and set(words).issubset(path_words):
            return _text(heading[1], 120)
    logo = re.search(r"https?://[^\s)]+/([\w-]+)-Restaurant-Logo[^\s)]*", markdown[:6000], re.I)
    if logo and urlsplit(logo[0]).hostname == urlsplit(url).hostname:
        logo_name = _words(logo[1]).replace(" ", "")
        if logo_name and host_name.startswith(logo_name):
            for brand in re.findall(r"\b[\w-]+[’']s\b", _without_markdown_links(markdown)):
                if _words(brand).replace(" ", "") == logo_name:
                    return brand
    return ""


def _menu_sources(pages, preferences, city):
    sources = []
    seen = set()
    fallback = None
    for page in pages:
        if not isinstance(page, dict):
            continue
        metadata = page.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        status = metadata.get("statusCode")
        if status is not None and str(status) != "200":
            continue
        url = _public_url(metadata.get("sourceURL")) or _public_url(page.get("url"))
        markdown = page.get("markdown")
        if not url or url in seen or not isinstance(markdown, str) or not markdown.strip():
            continue
        markdown = markdown[:120_000]
        if "the page you were looking for because it doesn't exist" in markdown[:400].casefold():
            continue
        title = _text(page.get("title") or metadata.get("title"), 120) or urlsplit(url).hostname
        description = _text(metadata.get("og:description") or metadata.get("description"), 600)
        reference = f"{title} {description} {unquote(urlsplit(url).path)} {markdown}"
        if not (_contains("menu", reference) or len(re.findall(r"\$\s*\d+", markdown)) >= 2):
            continue
        seen.add(url)
        restaurant = (_ordering_menu_restaurant(title, url, markdown)
                      or _official_menu_restaurant(title, metadata, url, markdown))
        excerpt = _menu_excerpt(markdown, preferences, city,
                                allow_plain_prices=urlsplit(url).hostname in {"slicelife.com", "www.slicelife.com"})
        if restaurant and not _contains(restaurant, f"{title} {excerpt}"):
            excerpt = f"Restaurant: {restaurant}\n\n{excerpt}"[:_EXCERPT_LIMIT]
        source = {"id": len(sources) + 1, "title": title, "url": url,
                  "excerpt": excerpt, "restaurant": restaurant}
        if _contains(city, reference):
            source["location"] = city
            sources.append(source)
        elif fallback is None:
            link = _location_link(markdown, url)
            if link:
                fallback = (source, link)
    if not sources and fallback:
        source, link = fallback
        evidence = _location_evidence(link, city)
        if evidence:
            source["excerpt"] = f"Restaurant location: {evidence}\n\n{source['excerpt']}"[:_EXCERPT_LIMIT]
            source["location"] = city
            sources.append(source)
    return sources


def _matches_cuisine(cuisine, title, excerpt, dish):
    if not cuisine or cuisine == "Any cuisine":
        return True
    if _contains(cuisine, f"{title} {excerpt}"):
        return True
    return any(_contains(signal, f"{title} {dish}") for signal in _CUISINE_SIGNALS.get(cuisine, ()))


def _taste_match(taste, dish, excerpt, restaurant=""):
    terms = TASTE_TERMS.get(taste, ())
    if not terms:
        return ""
    if taste == "Spicy":
        terms += _SPICY_SIGNALS
    lines = excerpt.splitlines()
    for index, line in enumerate(lines):
        if not _contains(dish, line):
            continue
        # Keep flavor evidence inside the item, including descriptions after a price.
        description = []
        for following in lines[index + 1:index + 5]:
            if not following.strip() or following.startswith(("#", "- ", "* ")):
                break
            if _CURRENCY_LINE.fullmatch(following.strip("*")):
                if description:
                    break
                continue
            description.append(following)
        evidence = " ".join((line, *description))
        if taste == "Spicy" and any(_contains(term, evidence) for term in TASTE_TERMS["Mild"]):
            continue
        for term in terms:
            if _contains(term, " ".join(description) if _contains(term, restaurant) else evidence):
                return term
    return ""


def _exact_menu_heading_picks(preferences, sources):
    """Use verifiable items from menus that identify their restaurants."""
    requested = set(_words(_text(preferences.get("dish"), 80)).split())
    picks = []
    taste = _text(preferences.get("taste"), 60)
    cuisine = _text(preferences.get("cuisine"), 60)
    for source in sources:
        restaurant = source.get("restaurant", "")
        if not restaurant:
            title = re.fullmatch(r"(.+?)\s+(?:[-–—]\s+)?Menu(?:\s*\|.*)?", source["title"], re.I)
            if not title:
                continue
            restaurant = title[1]
            host = (urlsplit(source["url"]).hostname or "").removeprefix("www.").split(".", 1)[0]
            if _words(host).replace(" ", "") != _words(restaurant).replace(" ", ""):
                continue
        lines = [line for line in source["excerpt"].splitlines() if line.strip()]
        dishes = []
        for dish, block in _menu_heading_blocks(lines):
            words = set(_words(dish).split())
            if (not requested.issubset(words) or words.intersection({"menu", "locations"})
                    or _words(dish) == _words(restaurant)):
                continue
            if not requested and not _item_evidence(block):
                continue
            if not _matches_cuisine(cuisine, source["title"], source["excerpt"], dish):
                continue
            if taste in TASTE_TERMS and not _taste_match(taste, dish, block, restaurant):
                continue
            dishes.append(dish)
        if dishes:
            dish = max(dishes, key=lambda item: _item_priority(item, taste))
            picks.append({"source_id": source["id"], "dish_name": dish, "restaurant_name": restaurant})
    return picks


def search_firecrawl(preferences, city):
    """Search current menu pages and return only dishes named in those pages."""
    from discover_ai import extract_menu_picks

    city = _text(city, 100)
    city_name = city.split(",", 1)[0].strip()
    sources = _menu_sources(_fetch_menus(city, preferences), preferences, city_name)
    if not sources:
        return []
    verified_headings = _exact_menu_heading_picks(preferences, sources)
    try:
        picks = extract_menu_picks(preferences, city, sources)
    except (RuntimeError, ValueError):
        if not verified_headings:
            raise FirecrawlDiscoverError("Discover found menu pages but could not read their dishes. Try again.") from None
        picks = []

    indexed = {source["id"]: source for source in sources}
    results = []
    restaurants = set()
    cuisine = _text(preferences.get("cuisine"), 60)
    taste = _text(preferences.get("taste"), 60)
    ordered_picks = sorted([*picks, *verified_headings],
                           key=lambda pick: _item_priority(pick["dish_name"], taste), reverse=True)
    for pick in ordered_picks:
        source = indexed.get(pick.get("source_id"))
        dish = _text(pick.get("dish_name"), 100)
        restaurant = _text(pick.get("restaurant_name"), 120)
        if not source or not _contains(dish, source["excerpt"]) or _words(restaurant) in restaurants:
            continue
        identity = f"{source['title']} {source['excerpt']}"
        if not _contains(restaurant, identity):
            continue
        if not _matches_cuisine(cuisine, source["title"], source["excerpt"], dish):
            continue
        taste_match = _taste_match(taste, dish, source["excerpt"], restaurant)
        if taste in TASTE_TERMS and not taste_match:
            continue
        location = _text(pick.get("location"), 120)
        restaurants.add(_words(restaurant))
        results.append({
            "dish_name": dish,
            "restaurant_name": restaurant,
            "cuisine": "" if cuisine == "Any cuisine" else cuisine,
            "taste_match": taste_match,
            "location": location if _contains(location, identity) else source.get("location", ""),
            "source_url": source["url"],
            "source_title": source["title"],
        })
        if len(results) >= _RESULT_LIMIT:
            break
    return results
