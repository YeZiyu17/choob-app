"""Checks Connect matching in static/connect-matches.js. Skipped when Node.js is not installed."""

import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
PHILLY = {"lat": 39.95, "lng": -75.16, "label": "Philadelphia, Chinatown"}


def run_matches(meals):
    script = (
        "globalThis.window = {};"
        f"require({json.dumps(str(ROOT / 'static' / 'connect-matches.js'))});"
        f"console.log(JSON.stringify(window.ChoobConnect.matchStamps({json.dumps(meals)})));"
    )
    out = subprocess.run([NODE, "-e", script], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "Node.js is not installed")
class ConnectMatchTests(unittest.TestCase):
    def test_no_meals_gives_profiles_to_explore(self):
        result = run_matches([])
        self.assertEqual(result["matches"], [])
        self.assertGreaterEqual(len(result["explore"]), 3)

    def test_shared_dish_type_ranks_profile_and_explains_why(self):
        result = run_matches([{"dish_name": "Spicy salmon roll", "location": PHILLY}])
        top = result["matches"][0]
        self.assertIn(top["id"], {"amelia", "maya"})
        self.assertEqual(top["shared"][0]["key"], "sushi")
        self.assertIn("Sushi", top["reason"])
        self.assertTrue(top["sharedDishes"])
        self.assertTrue(all(d["key"] != "sushi" for d in top["suggestions"]))

    def test_every_dish_in_a_multi_dish_meal_counts(self):
        meal = {"dish_name": "Pork gyoza", "source": "snap", "dishes": [
            {"dish_name": "Pork gyoza"}, {"dish_name": "Tonkotsu ramen"}]}
        keys = {t["key"] for t in run_matches([meal])["stampTypes"]}
        self.assertEqual(keys, {"dumplings", "ramen"})

    def test_meals_without_location_still_count(self):
        result = run_matches([{"dish_name": "Butter chicken"}])
        self.assertEqual(result["matches"][0]["id"], "priya")

    def test_cuisine_overlap_matches_without_same_dish(self):
        result = run_matches([{"dish_name": "Katsu curry", "cuisine": "Japanese"}])
        ids = {m["id"] for m in result["matches"]}
        self.assertTrue({"amelia", "maya"} & ids)
        maya = next(m for m in result["matches"] if m["id"] == "maya")
        self.assertIn("Japanese", maya["sharedCuisines"])

    def test_same_city_adds_to_score(self):
        with_city = run_matches([{"dish_name": "Margherita pizza", "location": PHILLY}])
        without = run_matches([{"dish_name": "Margherita pizza"}])
        leo = lambda r: next(m for m in r["matches"] if m["id"] == "leo")
        self.assertTrue(leo(with_city)["sameCity"])
        self.assertGreater(leo(with_city)["score"], leo(without)["score"])

    def test_unsupported_names_are_ignored(self):
        result = run_matches([{"dish_name": "Unknown"}, {"dish_name": "<script>"}])
        self.assertEqual(result["stampTypes"], [])


if __name__ == "__main__":
    unittest.main()
