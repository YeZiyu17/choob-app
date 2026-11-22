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
        for endpoint in ("/api/recognize", "/api/reverse-geocode", "/api/discover/chat", "/api/recommendation-summary"):
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

    def test_snap_review_exposes_editable_grouped_meal_controls(self):
        ids = set(self.parser.ids)
        self.assertTrue({
            "replaceSnapPhoto", "correctedDish", "extraMealDishes",
            "addMealDish", "removeFirstMealDish", "mealReviewSummary",
            "saveRecognizedDish", "snapSaveSuccess", "snapSaveSuccessMessage",
        }.issubset(ids))
        self.assertIn("will be logged together as one meal", self.html)
        self.assertIn("dishes,\n        image", self.html)
        self.assertIn("const MAX_MEAL_DISHES = 12", self.html)
        self.assertNotIn("% relative score", self.html)
        self.assertIn("Confirmation required", self.html)

    def test_snap_rescans_preserve_corrections_and_removed_suggestions(self):
        self.assertIn("primaryDishEdited", self.html)
        self.assertIn("dismissedSuggestions", self.html)
        self.assertIn("entry.suggestion&&!entry.edited", self.html)
        self.assertIn("Your photo and meal edits are still here", self.html)

    def test_snap_submission_has_both_click_and_storage_duplicate_guards(self):
        self.assertIn("if(mealSaveInFlight)return", self.html)
        self.assertIn("snap_draft_id:mealDraftId", self.html)
        self.assertIn("submittedDraftIndex", self.html)
        self.assertIn("source:'snap'", self.html)
        self.assertIn("want_to_try", self.html)

    def test_snap_persists_meal_location_and_per_dish_feedback(self):
        ids = set(self.parser.ids)
        self.assertTrue({
            "mealRestaurantName", "mealAddress", "primaryDishRating", "primaryDishNote",
        }.issubset(ids))
        for key in ("restaurant_name,", "address,", "rating:dishRating", "note:note.value.trim()"):
            self.assertIn(key, self.html)
        self.assertIn("item.location.label", self.html)
        self.assertIn("dishRating!==null", self.html)
        self.assertIn("dishRating<1||dishRating>5", self.html)
        self.assertIn("hasValidSnapDishFeedback", self.html)

    def test_snap_address_lookup_preserves_manual_edits_and_latest_pin(self):
        self.assertIn("addressLookupVersion", self.html)
        self.assertIn("addressEditVersion", self.html)
        self.assertIn("addressLookupRequest?.abort()", self.html)
        self.assertIn("editVersion!==addressEditVersion", self.html)
        self.assertIn("Address lookup failed. The pin is still selected", self.html)

    def test_snap_ranked_guesses_and_star_controls_are_accessible(self):
        self.assertIn("How Snap works", self.html)
        self.assertIn("Guesses for the whole photo", self.html)
        self.assertIn("Match score", self.html)
        self.assertIn("role','radiogroup", self.html)
        self.assertIn("role','radio", self.html)
        self.assertIn("ArrowRight", self.html)
        self.assertIn("Clear rating", self.html)


if __name__ == "__main__":
    unittest.main()
