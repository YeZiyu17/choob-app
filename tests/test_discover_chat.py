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
        self.assertEqual(eggplant["why"], "Its name on the menu, “Spicy Eggplant”, fits the spicy Chinese food you asked for.")
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
        reasons = {item["dish_name"]: item["why"] for item in results}
        self.assertEqual(reasons["Arancini"],
                         "You asked for crispy Italian food, and its menu listing says “Fried risotto balls with mozzarella”.")
        self.assertEqual(reasons["Fried Calamari"],
                         "Its name on the menu, “Fried Calamari”, fits the crispy Italian food you asked for.")

    def test_reasons_restate_the_request_and_quote_only_checked_menu_text(self):
        from discover_tavily import _why

        cases = [
            ({"cuisine": "Japanese", "taste": "Fresh & light", "dish": "sushi"}, "", "Omakase", "pristine raw fish",
             "You asked for fresh, light sushi, and its menu listing says “pristine raw fish”."),
            ({"cuisine": "Chinese", "taste": "Spicy", "dish": ""}, "Sichuan", "Mapo Tofu", "chili oil.",
             "You asked for spicy Sichuan food, and its menu listing says “chili oil”."),
            ({"cuisine": "Japanese", "taste": "Rich & creamy", "dish": "creamy ramen"}, "", "Tonkotsu", "rich broth",
             "You asked for creamy ramen, and its menu listing says “rich broth”."),
            ({"cuisine": "Thai", "taste": "Any flavor", "dish": ""}, "", "Pad See Ew", "",
             "You asked for Thai food, and this menu lists “Pad See Ew”."),
            ({"cuisine": "Any cuisine", "taste": "Any flavor", "dish": ""}, "", "Bibimbap", "with gochujang",
             "You left it open, so here’s a dish from this menu: “Bibimbap”, described as “with gochujang”."),
        ]
        for preferences, region, dish, evidence, expected in cases:
            with self.subTest(dish=dish):
                self.assertEqual(_why(preferences, region, dish, evidence), expected)

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

    def test_flavor_is_asked_once_then_any_flavor_is_searched(self):
        from discover_chat import discover_turn

        searched = []

        def recommend(preferences):
            searched.append(dict(preferences))
            return [{"dish_name": "Pho Tai", "restaurant_name": "Pho Fixture"}]

        def infer(message, previous, **_options):
            # Gemini reads "just pho" and "pho please" as the dish again, with no flavor.
            return {"dish": "pho"} if "pho" in message else {}

        first = discover_turn("pho", {}, infer=infer, recommend=recommend, online_city="Philadelphia")
        self.assertEqual(first["stage"], "taste")
        self.assertEqual(searched, [])
        for answer in ("just pho", "pho please", "no preference", "随便", "whatever", "idk"):
            with self.subTest(answer=answer):
                searched.clear()
                reply = discover_turn(answer, first["preferences"], infer=infer, recommend=recommend,
                                      online_city="Philadelphia")
                self.assertNotEqual(reply["stage"], "taste")
                self.assertEqual(searched[0]["taste"], "Any flavor")
                self.assertEqual(searched[0]["dish"], "pho")

    def test_a_flavor_named_in_the_follow_up_is_still_used(self):
        from discover_chat import discover_turn

        searched = []
        first = discover_turn("pho", {}, infer=lambda *_a, **_k: {"dish": "pho"},
                              recommend=lambda p: searched.append(dict(p)) or [], online_city="Philadelphia")
        discover_turn("just spicy", first["preferences"], infer=lambda *_a, **_k: {"taste": "Spicy"},
                      recommend=lambda p: searched.append(dict(p)) or [], online_city="Philadelphia")
        self.assertEqual(searched[0]["taste"], "Spicy")

    def test_gemini_busy_responses_are_retried_before_giving_up(self):
        import discover_gemini

        def reply(status, body=None):
            response = Mock(status_code=status)
            response.json.return_value = body or {}
            return response

        ok = reply(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"taste": "Spicy"}'}]}}]})
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             patch.object(discover_gemini, "sleep") as pause, \
             patch("requests.post", side_effect=[reply(503), reply(503), ok]) as post:
            result = discover_gemini._generate_json("x", {}, {}, phase="test", max_tokens=10, read_timeout=5)
        self.assertEqual(result, {"taste": "Spicy"})
        self.assertEqual(post.call_count, 3)
        self.assertEqual(pause.call_count, 2)

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             patch.object(discover_gemini, "sleep"), \
             patch("requests.post", side_effect=[reply(503)] * 3) as post:
            with self.assertRaisesRegex(discover_gemini.GeminiDiscoverError, "temporarily busy"):
                discover_gemini._generate_json("x", {}, {}, phase="test", max_tokens=10, read_timeout=5)
        self.assertEqual(post.call_count, 3)

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}), \
             patch.object(discover_gemini, "sleep") as pause, \
             patch("requests.post", side_effect=[reply(429)]) as post:
            with self.assertRaisesRegex(discover_gemini.GeminiDiscoverError, "quota"):
                discover_gemini._generate_json("x", {}, {}, phase="test", max_tokens=10, read_timeout=5)
        self.assertEqual((post.call_count, pause.call_count), (1, 0))

    def test_neighborhood_search_keeps_picks_inside_the_area(self):
        # Each menu: (restaurant, dish, address line). Only the first two are in Koreatown.
        fixtures = [
            ("Seoul Kitchen", "Kimchi Fried Rice", "3600 Wilshire Blvd, Los Angeles, CA 90010"),
            ("Ktown Pocha", "Spicy Rice Cakes", "Located in the heart of Koreatown"),
            ("Santa Monica Grill", "Spicy Bulgogi", "1200 Main St, Los Angeles, CA 90401"),
            ("Valley Tofu House", "Spicy Soft Tofu", "500 Valley Blvd, Alhambra, CA 91801"),
        ]
        menus, picks = [], {}
        for index, (restaurant, dish, address) in enumerate(fixtures, 1):
            url = f"https://korean-{index}.example/menu"
            menus.append({"title": f"{restaurant} Menu", "url": url,
                          "content": f"{address}\n## {dish}\nSpicy gochujang sauce"})
            picks[url] = {"dish_name": dish, "restaurant_name": restaurant, "cuisine": "Korean",
                          "location": "Los Angeles", "taste_evidence": "Spicy gochujang sauce"}
        queries, gemini_cities = [], []

        def provider_reply(url, **options):
            payload = options["json"]
            if url == "https://api.tavily.com/search":
                queries.append(payload["query"])
                return Mock(status_code=200, **{"json.return_value": {"results": menus}})
            message = json.loads(payload["contents"][0]["parts"][0]["text"])
            gemini_cities.append(message["city"])
            selected = [{"source_id": source["id"], **picks[source["url"]]} for source in message["menu_sources"]]
            return Mock(status_code=200, **{"json.return_value": {"candidates": [{
                "finishReason": "STOP", "content": {"parts": [{"text": json.dumps({"results": selected})}]},
            }]}})

        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Los Angeles"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch("requests.post", side_effect=provider_reply):
            config = self.client.get("/api/discover/config").get_json()
            self.assertEqual(config["neighborhoods"]["Los Angeles"],
                             ["Downtown", "Koreatown", "San Gabriel Valley"])
            self.assertIn("Flushing", config["neighborhoods"]["New York"])
            self.assertNotIn("Chicago", config["neighborhoods"])
            response = self.client.post("/api/discover/chat", json={
                "message": "Spicy", "preferences": {"cuisine": "Korean"},
                "city": "Los Angeles", "neighborhood": "Koreatown",
            })
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data["neighborhood"], "Koreatown")
            self.assertIn("Koreatown, Los Angeles", data["reply"])
            self.assertEqual({item["restaurant_name"] for item in data["results"]}, {"Seoul Kitchen", "Ktown Pocha"})
            for item in data["results"]:
                self.assertEqual((item["neighborhood"], item["location"]), ("Koreatown", "Koreatown, Los Angeles"))
            self.assertTrue(all(query.startswith("Koreatown Los Angeles") for query in queries))
            self.assertTrue(all(city == "Koreatown, Los Angeles" for city in gemini_cities))

            # The San Gabriel Valley is outside the city of Los Angeles; its own towns count as the area.
            queries.clear()
            valley = self.client.post("/api/discover/chat", json={
                "message": "Spicy", "preferences": {"cuisine": "Korean"},
                "city": "Los Angeles", "neighborhood": "San Gabriel Valley",
            }).get_json()
            self.assertEqual([item["restaurant_name"] for item in valley["results"]], ["Valley Tofu House"])

            # A whole-city search is unchanged, and an unknown or mismatched area is refused.
            whole_city = self.client.post("/api/discover/chat", json={
                "message": "Spicy", "preferences": {"cuisine": "Korean"}, "city": "Los Angeles",
            }).get_json()
            self.assertNotIn("neighborhood", whole_city)
            self.assertNotIn("Valley Tofu House", {item["restaurant_name"] for item in whole_city["results"]})
            for city, area in (("Los Angeles", "Flushing"), ("Los Angeles", "Beverly Hills"), ("Chicago", "Loop")):
                with self.subTest(city=city, area=area):
                    refused = self.client.post("/api/discover/chat", json={
                        "message": "Spicy", "preferences": {"cuisine": "Korean"}, "city": city, "neighborhood": area,
                    })
                    self.assertEqual(refused.status_code, 400)

    def test_neighborhood_zip_codes_do_not_match_prices_or_longer_numbers(self):
        from discover_areas import area_spec

        koreatown = area_spec("Los Angeles", "Koreatown")
        self.assertTrue(koreatown["zip"].search("Los Angeles, CA 90010"))
        self.assertTrue(koreatown["zip"].search("CA 90005-1234"))
        for text in ("$90010", "Order #900105", "1.90010", "CA 90012"):
            with self.subTest(text=text):
                self.assertFalse(koreatown["zip"].search(text))
        self.assertIsNone(area_spec("Los Angeles", "Flushing"))

    def _menu_search_fixture(self, fixtures, city="Philadelphia"):
        """Fake Tavily + Gemini: every fixture menu is found, and Gemini picks every dish."""
        menus, picks, gemini_requests = [], {}, []
        for index, (restaurant, dish, cuisine) in enumerate(fixtures, 1):
            url = f"https://menu-{index}.example/menu"
            menus.append({"title": f"{restaurant} {cuisine} Menu, {city}", "url": url,
                          "content": f"## {dish}\nA house favorite"})
            picks[url] = {"dish_name": dish, "restaurant_name": restaurant, "cuisine": cuisine,
                          "location": city, "taste_evidence": ""}

        def provider_reply(url, **options):
            payload = options["json"]
            if url == "https://api.tavily.com/search":
                return Mock(status_code=200, **{"json.return_value": {"results": menus}})
            message = json.loads(payload["contents"][0]["parts"][0]["text"])
            gemini_requests.append({"message": message, "instructions": payload["systemInstruction"]["parts"][0]["text"]})
            selected = [{"source_id": source["id"], **picks[source["url"]]} for source in message["menu_sources"]]
            return Mock(status_code=200, **{"json.return_value": {"candidates": [{
                "finishReason": "STOP", "content": {"parts": [{"text": json.dumps({"results": selected})}]},
            }]}})
        return provider_reply, gemini_requests

    def test_ratings_rank_liked_cuisines_first_and_skip_low_rated_dishes(self):
        provider_reply, gemini_requests = self._menu_search_fixture([
            ("Taco Spot", "Carne Asada Tacos", "Mexican"),
            ("Kaze Sushi Bar", "Salmon Nigiri", "Japanese"),
            ("Golden Wok", "Chicken Fried Rice", "Chinese"),
        ])
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Philadelphia"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch("requests.post", side_effect=provider_reply):
            response = self.client.post("/api/discover/chat", json={
                "message": "Any flavor", "preferences": {"cuisine": "Any cuisine"},
                "taste_profile": {"liked_cuisines": ["japanese", "Klingon"], "disliked_dishes": ["fried rice"]},
            })
        self.assertEqual(response.status_code, 200)
        results = response.get_json()["results"]
        self.assertEqual([item["restaurant_name"] for item in results], ["Kaze Sushi Bar", "Taco Spot"])
        self.assertEqual(results[0]["taste_match"], "You rated Japanese highly")
        self.assertNotIn("taste_match", results[1])
        self.assertEqual(gemini_requests[0]["message"]["preferences"]["favored_cuisines"], ["Japanese"])
        self.assertIn("favored_cuisines", gemini_requests[0]["instructions"])

    def test_planning_with_a_partner_explains_shared_tastes_and_skips_their_low_ratings(self):
        provider_reply, _ = self._menu_search_fixture([
            ("Lemongrass Corner", "Shrimp Pad Thai", "Thai"),
            ("Kaze Sushi Bar", "Salmon Nigiri", "Japanese"),
            ("Forno Nove", "Margherita Pizza", "Italian"),
        ])
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Philadelphia"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch("requests.post", side_effect=provider_reply):
            response = self.client.post("/api/discover/chat", json={
                "message": "Any flavor", "preferences": {"cuisine": "Any cuisine"},
                "taste_profile": {"liked_cuisines": ["Japanese", "Italian"], "disliked_dishes": []},
                "partner": {"name": "Amelia", "liked_cuisines": ["Thai", "Japanese"],
                            "disliked_dishes": ["Margherita pizza"]},
            })
            self.assertEqual(response.status_code, 200)
            results = response.get_json()["results"]
            self.assertEqual([(item["restaurant_name"], item.get("taste_match")) for item in results], [
                ("Kaze Sushi Bar", "You and Amelia both like Japanese"),
                ("Lemongrass Corner", "Amelia likes Thai"),
            ])
            for partner in ({"liked_cuisines": ["Thai"]}, {"name": "<script>", "liked_cuisines": ["Thai"]}, "Amelia"):
                with self.subTest(partner=partner):
                    refused = self.client.post("/api/discover/chat", json={
                        "message": "Any flavor", "preferences": {"cuisine": "Any cuisine"}, "partner": partner,
                    })
                    self.assertEqual(refused.status_code, 400)

    def test_searches_without_ratings_are_unchanged(self):
        from discover_tastes import clean_taste_profile, combine_tastes

        self.assertIsNone(clean_taste_profile({"liked_cuisines": ["Martian"], "disliked_dishes": ["", 5]}))
        self.assertIsNone(combine_tastes(None, None))
        with patch.dict(backend.app.config, DISCOVER_PROVIDER="gemini_tavily", DISCOVER_CITY="Seattle"), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key", "TAVILY_API_KEY": "test-key"}), \
             patch.object(backend, "search_tavily", return_value=[]) as search:
            self.client.post("/api/discover/chat", json={
                "message": "Spicy", "preferences": {"cuisine": "Thai"}, "city": "Los Angeles",
                "taste_profile": {"liked_cuisines": [], "disliked_dishes": []},
            })
        search.assert_called_once_with({"cuisine": "Thai", "taste": "Spicy", "dish": ""}, "Los Angeles",
                                       select_picks=backend.select_gemini_picks)
