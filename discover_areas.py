"""Neighborhoods Discover can search within, and the address evidence that places a menu there.

A menu page counts as being in a neighborhood only when its title or the excerpt shown to Gemini
names one of the neighborhood's places or carries one of its ZIP codes. Some neighborhoods also list
towns to search by name when the area-wide search finds too few menus; every town is also one of
the area's places, so its menus still pass the same check. Area names alone are not
enough for broad labels such as "Chinatown", so each entry is scoped to its city.
"""

from __future__ import annotations

import re

NEIGHBORHOODS = {
    "Los Angeles": {
        "Downtown": {
            "places": ("Downtown Los Angeles", "Downtown LA", "DTLA", "Little Tokyo", "Arts District",
                       "Historic Core", "Chinatown"),
            "zip": r"900(?:12|13|14|15|17|21|71)",
            "towns": ("Little Tokyo", "Chinatown", "Arts District", "Historic Core"),
        },
        "Koreatown": {
            "places": ("Koreatown", "K-Town", "Ktown"),
            "zip": r"900(?:05|06|10|20)",
        },
        "San Gabriel Valley": {
            "places": ("San Gabriel Valley", "San Gabriel", "Alhambra", "Monterey Park", "Rosemead", "Arcadia",
                       "Temple City", "El Monte", "Rowland Heights", "Pasadena"),
            "zip": r"91(?:00[67]|10[1-7]|7(?:3[1-3]|48|5[45]|70|7[568]|80)|80[13])",
            "towns": ("San Gabriel", "Alhambra", "Monterey Park", "Rosemead", "Arcadia", "Temple City"),
        },
    },
    "New York": {
        "Manhattan": {"places": ("Manhattan",), "zip": r"10[0-2]\d\d"},
        "Flushing": {"places": ("Flushing",), "zip": r"113(?:54|55|58)"},
        "Brooklyn": {"places": ("Brooklyn",), "zip": r"112\d\d"},
    },
    "Philadelphia": {
        "Center City": {
            "places": ("Center City", "Rittenhouse", "Old City", "Washington Square West", "Chinatown"),
            "zip": r"191(?:02|03|06|07)",
            "towns": ("Chinatown", "Rittenhouse", "Old City", "Washington Square West"),
        },
        "South Philly": {
            "places": ("South Philadelphia", "South Philly", "East Passyunk", "Passyunk", "Bella Vista",
                       "Queen Village", "Italian Market"),
            "zip": r"191(?:45|46|47|48)",
            "towns": ("East Passyunk", "Italian Market", "Bella Vista", "Queen Village"),
        },
        "University City": {"places": ("University City",), "zip": r"19104"},
    },
}


_STATES = {"Los Angeles": "CA", "New York": "NY", "Philadelphia": "PA"}


def neighborhood_options(cities):
    """List the neighborhoods offered for each supported city, in display order."""
    return {city: list(NEIGHBORHOODS[city]) for city in cities if city in NEIGHBORHOODS}


def area_spec(city, neighborhood):
    """Return the matcher for a supported neighborhood, or None for the whole city."""
    entry = NEIGHBORHOODS.get(city, {}).get(neighborhood)
    if not entry:
        return None
    zip_code = re.compile(rf"(?<![\d$.,]){entry['zip']}(?:-\d{{4}})?(?!\d)")
    return {"label": neighborhood, "city": city, "places": entry["places"], "zip": zip_code,
            "towns": entry.get("towns", ()), "state": _STATES.get(city, "")}


def town_rounds(area, *, start_late=False, per_round=2, rounds=2):
    """Groups of the area's own towns to search by name when the area-wide search finds too few menus.

    "Show more" starts from the later towns so it reaches menus the first search did not.
    """
    towns = list(area["towns"]) if area else []
    if start_late:
        towns = towns[per_round:] + towns[:per_round]
    return [towns[index:index + per_round] for index in range(0, min(len(towns), per_round * rounds), per_round)]
