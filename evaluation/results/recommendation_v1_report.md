# Recommendation integration report — 2026-10-23

## Data and actual method

- Inputs: 484 real cleaned reviews and a 5,855-row restaurant catalog supplied by the project team. All 484 reviews join to 50 restaurants; no required-field gaps or duplicate review IDs were found.
- Extraction: Codex-assisted annotation with exact quotation validation. A 25-review AI spot audit and a targeted screen were followed by 11 corrections (four removed items and seven sentiment corrections). This is not a human audit or an accuracy estimate. Free Colab GPU quota was unavailable, so Qwen extraction was not executed.
- Output: 835 review–dish mentions; 380 reviews with dishes, 104 with no extracted dish, zero failed reviews; 711 aggregated restaurant–dish pairs across 50 restaurants.
- Embeddings: actual local `sentence-transformers/all-MiniLM-L6-v2` inference, 711 × 384 normalized float32 matrix. No model weights were fine-tuned.
- Ranking: `0.85 * cosine_similarity + 0.15 * smoothed_dish_sentiment`, with the sentiment formula in the export manifest. Scores are uncalibrated rankings.

## Completed checks

- All 27 regression checks passed: 23 recommendation/data/API checks and four recognition policy checks. These use synthetic fixtures and mocks, not a labeled relevance benchmark.
- Actual MiniLM + Flask test-client smoke test: five preferences returned HTTP 200 and five distinct top-five lists, all referencing actual export rows. Queries include cheesesteak, sushi, mushrooms, dessert and spicy food.
- Three vector rows were regenerated from CSV descriptions; maximum absolute difference was `1.2665987014770508e-07`. Full CSV/NPY hashes also match the manifest.
- Malformed JSON returns HTTP 400. A common explicit vegetarian request returns HTTP 422 with a clear unsupported-request explanation because the source reviews cannot verify dietary suitability.
- The local Flask page was checked in the browser: a dessert preference renders real recommendation cards, and an explicit vegetarian request displays the unsupported-request message. This supplements the separate test-client report, whose `served_over_network` field correctly remains false.

Machine-readable model/API results and query-level outputs are in `recommendation_smoke.json`. Warm request times exclude model loading, process startup, network and browser rendering.

## Limits and next evaluation

This is a functioning prototype, not a verified recommendation-quality result. Sushi queries can return other seafood below the first result. Plural/spelling variants such as “Cheesecake” and “Cheesecakes” may remain separate. Coverage is limited to 50 sampled restaurants; historical review mentions do not establish current menus or ingredient lists. The existing embedding model is intended here for English preferences; multilingual relevance has not been evaluated.

Person 5 should independently label dish extraction and sentiment on a fixed held-out review sample, and rate top-five relevance for a fixed preference set against a baseline. Person 2 can expand coverage by providing more cleaned reviews. Person 4 can deploy Flask and validate model loading and the complete Snap/Discover → Collect flow on the chosen host. The local run is not a shared hosted deployment.
