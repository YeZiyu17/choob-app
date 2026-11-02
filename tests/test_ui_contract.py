"""Fast checks for the framework-free Choob UI and its backend contract hooks."""

from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class _UIParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.nav_targets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        if "data-nav" in values:
            self.nav_targets.append(values["data-nav"])


class UIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.parser = _UIParser()
        cls.parser.feed(cls.html)

    def test_all_ids_are_unique(self):
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))

    def test_four_step_screens_and_navigation_targets_exist(self):
        ids = set(self.parser.ids)
        expected = {"snapScreen", "collectionScreen", "recommendScreen", "connectScreen"}
        self.assertTrue(expected.issubset(ids))
        self.assertTrue(expected.issubset(set(self.parser.nav_targets)))

    def test_live_ui_keeps_backend_contracts(self):
        for endpoint in ("/api/recognize", "/api/recommend", "/api/recommendation-summary"):
            self.assertIn(endpoint, self.html)
        for element_id in (
            "photoUpload", "shutter", "scanResult", "correctedDish",
            "preferenceInput", "findDishes", "liveRecommendations",
            "savedDishList", "dishDetail", "detailTitle", "closeDetail",
        ):
            self.assertIn(element_id, self.parser.ids)

    def test_mobile_and_accessibility_guards_are_present(self):
        self.assertIn("-webkit-text-size-adjust:100%", self.html)
        self.assertIn("prefers-reduced-motion:reduce", self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertNotIn("�", self.html)


if __name__ == "__main__":
    unittest.main()
