"""Check Discover's multi-turn filtering and source selection without network calls."""

import json
from unittest import TestCase
from unittest.mock import Mock, patch

import pandas as pd

import app as backend


class DiscoverChatTests(TestCase):
    def setUp(self):
        self.client = backend.app.test_client()

    def test_two_chip_turns_require_real_cuisine_and_taste_evidence(self):
        cases = [
            ("spicy tuna roll", "Right restaurant", "Japanese/Sushi/Ramen", "[]", 1),
            ("plain sushi", "Wrong flavor", "Japanese/Sushi/Ramen", "[]", 1),
            ("not spicy tuna roll", "Opposite flavor", "Japanese/Sushi/Ramen", "[]", 1),
            ("spicy pizza", "Wrong cuisine", "Italian/Pizza", "[]", 1),
            ("spicy ramen", "Historically closed", "Japanese/Sushi/Ramen", "[]", 0),
        ]
        frame = pd.DataFrame(cases, columns=("dish_name_normalized", "restaurant_name", "cuisine_group",
                                            "taste_tags_clean", "historical_is_open"))
        frame = frame.assign(review_count=2, positive_count=2, negative_count=0, mixed_count=0, neutral_count=0)
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="local"), \
             patch.object(backend, "load_recommender", return_value=(frame, None, None)), \
             patch.object(backend, "infer_preferences") as ai:
            first = self.client.post("/api/discover/chat", json={"message": "Japanese"}).get_json()
            self.assertEqual(first["stage"], "taste")
            result = self.client.post("/api/discover/chat", json={
                "message": "Spicy", "preferences": first["preferences"],
            }).get_json()
        ai.assert_not_called()
        self.assertEqual(result["stage"], "results")
        self.assertEqual([(row["restaurant_name"], row["taste_match"]) for row in result["results"]],
                         [("Right restaurant", "spicy")])

    def test_online_mode_with_no_key_reports_configuration_gap(self):
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="openai"), \
             patch.dict("os.environ", {"OPENAI_API_KEY": ""}), \
             patch.object(backend, "local_discover_picks") as local:
            response = self.client.post("/api/discover/chat", json={"message": "Japanese"})
        local.assert_not_called()
        self.assertEqual(response.status_code, 503)
        self.assertIn("API key", response.get_json()["error"])

    def test_gemini_tavily_reports_missing_key_without_searching(self):
        for gemini, tavily in (("test-key", ""), ("", "test-key")):
            with self.subTest(gemini_configured=bool(gemini)), \
                 patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Seattle"), \
                 patch.dict("os.environ", {"GEMINI_API_KEY": gemini, "GOOGLE_API_KEY": "", "TAVILY_API_KEY": tavily}), \
                 patch.object(backend, "search_tavily") as search, \
                 patch.object(backend, "local_discover_picks") as local:
                settings = self.client.get("/api/discover/config").get_json()
                self.assertEqual((settings["provider"], settings["online_ready"]), ("gemini_tavily", False))
                self.assertEqual(settings["city"], "Seattle")
                self.assertIn("Seattle", settings["cities"])
                self.assertIn("Los Angeles", settings["cities"])
                response = self.client.post("/api/discover/chat", json={"message": "Japanese"})
                self.assertEqual(response.status_code, 503)
                self.assertIn("API keys", response.get_json()["error"])
                search.assert_not_called()
                local.assert_not_called()

    def test_gemini_tavily_routes_chips_and_free_text_to_the_same_online_flow(self):
        pick = {"dish_name": "Chicken Katsu", "restaurant_name": "Menu fixture", "cuisine": "Japanese",
                "note": "Panko-breaded chicken for a crunchy bite.", "source_url": "https://example.com/menu"}
        prefs = {"cuisine": "Japanese", "taste": "Crispy", "dish": ""}

        def infer_preferences(message, previous, **_options):
            self.assertEqual((message, previous), ("想吃脆一点的", {"cuisine": "Japanese", "taste": "", "dish": ""}))
            return {"taste": "Crispy"}

        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Seattle"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch.object(backend, "infer_gemini", side_effect=infer_preferences) as infer, \
             patch.object(backend, "search_tavily", return_value=[pick]) as search, \
             patch.object(backend, "local_discover_picks") as local:
            self.assertTrue(self.client.get("/api/discover/config").get_json()["online_ready"])
            first = self.client.post("/api/discover/chat", json={"message": "Japanese", "city": "Los Angeles"}).get_json()
            self.assertEqual(first["stage"], "taste")
            search.assert_not_called()
            for message in ("Crispy", "想吃脆一点的"):
                response = self.client.post("/api/discover/chat", json={
                    "message": message, "preferences": first["preferences"], "city": "Los Angeles",
                })
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json()["results"], [pick])
                self.assertEqual(response.get_json()["provider"], "gemini_tavily")
                self.assertEqual(response.get_json()["city"], "Los Angeles")
                self.assertIn("Los Angeles", response.get_json()["reply"])
                search.assert_called_once_with(prefs, "Los Angeles", select_picks=backend.select_gemini_picks)
                search.reset_mock()
            infer.assert_called_once()
            local.assert_not_called()

    def test_online_city_must_be_a_supported_option(self):
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="firecrawl", DISCOVER_CITY="Seattle"), \
             patch.object(backend, "search_firecrawl") as search:
            response = self.client.post("/api/discover/chat", json={
                "message": "Crispy", "preferences": {"cuisine": "Italian"}, "city": "Unsupported city",
            })
        self.assertEqual(response.status_code, 400)
        search.assert_not_called()

    def test_more_dishes_reuses_city_and_preferences_without_interpreting_a_message(self):
        preferences = {"cuisine": "Chinese", "taste": "Spicy", "dish": "eggplant", "region": "Sichuan"}
        excluded = ["First Restaurant", "Second Restaurant"]
        pick = {"dish_name": "Sichuan Spicy Eggplant", "restaurant_name": "Third Restaurant",
                "source_url": "https://third-restaurant.example/menu"}
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Philadelphia"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch.object(backend, "infer_gemini") as infer, \
             patch.object(backend, "search_tavily", return_value=[pick]) as search:
            response = self.client.post("/api/discover/chat", json={
                "action": "more", "city": "Los Angeles", "preferences": preferences,
                "exclude_restaurants": excluded,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["city"], "Los Angeles")
        self.assertEqual(response.get_json()["results"], [pick])
        search.assert_called_once_with(preferences, "Los Angeles", select_picks=backend.select_gemini_picks,
                                       exclude_restaurants=excluded)
        infer.assert_not_called()

    def test_more_dishes_rejects_invalid_restaurant_exclusions_before_searching(self):
        invalid_exclusions = (None, "First Restaurant", [], [42], [" "], ["x" * 121], ["Restaurant"] * 61)
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Philadelphia"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch.object(backend, "infer_gemini") as infer, \
             patch.object(backend, "search_tavily") as search:
            for excluded in invalid_exclusions:
                with self.subTest(excluded=excluded):
                    response = self.client.post("/api/discover/chat", json={
                        "action": "more", "city": "Los Angeles",
                        "preferences": {"cuisine": "Chinese", "taste": "Spicy", "region": "Sichuan"},
                        "exclude_restaurants": excluded,
                    })
                    self.assertEqual(response.status_code, 400)
        search.assert_not_called()
        infer.assert_not_called()

    def test_chinese_spicy_ranks_dish_evidence_and_offers_optional_region_filter(self):
        fixtures = [
            ("Pearl Kitchen", "Wontons", "Served in chili oil", "chili oil", "Sichuan cuisine"),
            ("River Kitchen", "Pork", "Not spicy.\n## Sichuan Tofu\nWith ginger.", "spicy", "Sichuan Tofu"),
            ("Red Lantern", "Sichuan Spicy Beef", "Tossed in spicy Sichuan sauce", "Spicy Beef", "Sichuan"),
            ("Jade Kitchen", "Spicy Eggplant", "Spicy Hot\nGarlic and peppers\n## Mapo Tofu\nServed in chili oil.", "Spicy Hot", ""),
        ]
        menus = [{"title": f"{restaurant} Chinese Menu in Philadelphia", "url": f"https://menu-{i}.example/menu",
                  "content": f"## {dish}\n{description}"}
                 for i, (restaurant, dish, description, _, _) in enumerate(fixtures)]
        menus[0]["title"] = "Pearl Kitchen | Sichuan cuisine menu in Philadelphia"
        menus[2]["content"] = "Sichuan Spicy Beef (S) 15.95 - (L) 18.95\nTossed in spicy Sichuan sauce"
        queries = []

        def provider_reply(url, **options):
            payload = options["json"]
            if url == "https://api.tavily.com/search":
                queries.append(payload["query"])
                return Mock(status_code=200, **{"json.return_value": {"results": menus}})
            message = json.loads(payload["contents"][0]["parts"][0]["text"])
            self.assertEqual(message["preferences"]["taste"], "Spicy")
            region = message["preferences"].get("region")
            selected = []
            for source in message["menu_sources"]:
                i = next(i for i, menu in enumerate(menus) if menu["url"] == source["url"])
                restaurant, dish, _, heat, region_quote = fixtures[i]
                row = {"source_id": source["id"], "dish_name": dish, "restaurant_name": restaurant,
                       "taste_evidence": heat, "cuisine": "Chinese", "location": "Philadelphia"}
                if region:
                    row["region_evidence"] = region_quote
                selected.append(row)
            return Mock(status_code=200, **{"json.return_value": {"candidates": [{
                "content": {"parts": [{"text": json.dumps({"results": selected})}]},
            }]}})

        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Philadelphia"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch("requests.post", side_effect=provider_reply):
            broad = self.client.post("/api/discover/chat", json={
                "message": "Spicy", "preferences": {"cuisine": "Chinese"},
            }).get_json()
            refined = self.client.post("/api/discover/chat", json={
                "message": "Sichuan", "preferences": broad["preferences"],
            }).get_json()
            again = self.client.post("/api/discover/chat", json={
                "message": "Any Chinese style", "preferences": refined["preferences"],
            }).get_json()

        self.assertEqual(broad["options"], ["Sichuan", "Hunan", "Cantonese"])
        self.assertEqual([item["dish_name"] for item in broad["results"]],
                         ["Sichuan Spicy Beef", "Spicy Eggplant", "Wontons"])
        beef, eggplant, wontons = broad["results"]
        self.assertIn("spicy Sichuan sauce", beef["why"])
        self.assertIn("chili oil", wontons["why"])
        self.assertNotIn("why", eggplant)
        self.assertIn("Spicy Eggplant", eggplant["note"])
        self.assertTrue(all("region" not in item for item in broad["results"]))
        self.assertEqual(refined["preferences"], {"cuisine": "Chinese", "taste": "Spicy", "dish": "", "region": "Sichuan"})
        self.assertEqual([(item["dish_name"], item.get("region"), item.get("menu_region")) for item in refined["results"]],
                         [("Sichuan Spicy Beef", "Sichuan", None), ("Wontons", None, "Sichuan")])
        self.assertTrue(any("Sichuan" in query for query in queries))
        self.assertEqual(again["preferences"], broad["preferences"])

    def test_gemini_tavily_looks_for_more_restaurants_and_checks_each_menu(self):
        fixtures = [
            ("Osteria One", "Pollo Milanese", "Breaded chicken with lemon", "#### 25\nBreaded chicken with lemon"),
            ("Osteria Two", "Arancini", "Fried risotto balls with mozzarella", "Fried risotto balls with mozzarella"),
            ("Osteria Three", "Fried Calamari", "Fried", "$14.00 Served with marinara\nBread Basket $4.00"),
            ("Osteria Four", "Pasta al Pomodoro", "Crispy coating", "Tomato and basil\n## Fried Zucchini\nCrispy coating"),
        ]
        menus, picks = [], {}
        for index, (restaurant, dish, evidence, description) in enumerate(fixtures, 1):
            url = f"https://osteria-{index}.example/menu"
            title = f"{restaurant} Italian Menu, Philadelphia"
            if index == 3:  # Reservation pages may show priced menu entries only in the excerpt.
                url = "https://www.opentable.com/r/osteria-three-philadelphia"
                title = f"{restaurant} - Philadelphia"
            menus.append({"title": title, "url": url, "content": f"## {dish}\n{description}"})
            picks[url] = {"dish_name": dish, "restaurant_name": restaurant, "cuisine": "Italian",
                          "location": "Philadelphia", "taste_evidence": evidence}
        queries = []

        def provider_reply(url, **options):
            payload = options["json"]
            if url == "https://api.tavily.com/search":
                query = payload["query"]
                self.assertIn("Philadelphia", query)
                self.assertIn("Italian", query)
                queries.append(query)
                results = menus[:1] if len(queries) == 1 else menus
                return Mock(status_code=200, **{"json.return_value": {"results": results}})
            self.assertTrue(url.startswith("https://generativelanguage.googleapis.com/"))
            message = json.loads(payload["contents"][0]["parts"][0]["text"])
            self.assertEqual(message["preferences"]["taste"], "Crispy")
            selected = [{"source_id": source["id"], **picks[source["url"]]}
                        for source in message["menu_sources"]]
            selected.reverse()  # The invalid claim must be rejected even if the model ranks it first.
            return Mock(status_code=200, **{"json.return_value": {"candidates": [{
                "finishReason": "STOP", "content": {"parts": [{"text": json.dumps({"results": selected})}]},
            }]}})

        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Philadelphia"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch("requests.post", side_effect=provider_reply):
            first = self.client.post("/api/discover/chat", json={"message": "Italian"}).get_json()
            response = self.client.post("/api/discover/chat", json={
                "message": "Crispy", "preferences": first["preferences"],
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(queries), 2)
        self.assertNotEqual(*queries)
        results = response.get_json()["results"]
        self.assertCountEqual([(item["restaurant_name"], item["dish_name"], item["source_url"]) for item in results],
                              [(restaurant, dish, menu["url"]) for (restaurant, dish, _, _), menu in zip(fixtures[:3], menus)])
        for item in results:
            self.assertIn(picks[item["source_url"]]["taste_evidence"], item["note"])
        calamari = next(item for item in results if item["dish_name"] == "Fried Calamari")
        self.assertIn("Fried Calamari", calamari["note"])

    def test_online_modes_route_to_menu_search_without_loading_local_reviews(self):
        pick = {"dish_name": "Spicy Ramen", "restaurant_name": "Menu fixture",
                "source_url": "https://example.com/menu"}
        providers = [("openai", "search_online", "test-only"), ("firecrawl", "search_firecrawl", "")]
        for provider, search_function, openai_key in providers:
            with self.subTest(provider=provider), \
                 patch.dict(backend.app.config, DISCOVER_PROVIDER=provider, DISCOVER_CITY="Seattle"), \
                 patch.dict("os.environ", {"OPENAI_API_KEY": openai_key, "FIRECRAWL_API_KEY": ""}), \
                 patch.object(backend, search_function, return_value=[pick]) as online, \
                 patch.object(backend, "local_discover_picks") as local:
                result = self.client.post("/api/discover/chat", json={
                    "message": "Spicy", "preferences": {"cuisine": "Japanese"},
                }).get_json()
                local.assert_not_called()
                online.assert_called_once_with({"cuisine": "Japanese", "taste": "Spicy", "dish": ""}, "Seattle")
                self.assertEqual((result["provider"], result["results"]), (provider, [pick]))
                self.assertEqual(result["options"], ["Any flavor"])

    def test_firecrawl_chips_return_verified_dishes_at_distinct_restaurants(self):
        pages = [
            {"title": f"{restaurant} Menu | Italian in Philadelphia", "url": f"https://{host}.example/menu",
             "markdown": f"# {restaurant} Menu\n## {dish}\n{description}\n$15"}
            for restaurant, host, dish, description in (
                ("Osteria One", "osteriaone", "Crispy Mozzarella", "Breaded mozzarella with pomodoro."),
                ("Osteria Two", "osteriatwo", "Chicken Milanese", "Crunchy breading with lemon."),
                ("Osteria Three", "osteriathree", "Spaghetti", "Pasta with tomato and basil."),
            )
        ]
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="firecrawl", DISCOVER_CITY="Philadelphia"), \
             patch("discover_firecrawl._fetch_menus", return_value=pages), \
             patch("discover_ai.extract_menu_picks", return_value=[]):
            first = self.client.post("/api/discover/chat", json={"message": "Italian"}).get_json()
            response = self.client.post("/api/discover/chat", json={
                "message": "Crispy", "preferences": first["preferences"],
            })
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual([(row["restaurant_name"], row["dish_name"]) for row in result["results"]],
                         [("Osteria One", "Crispy Mozzarella"), ("Osteria Two", "Chicken Milanese")])
