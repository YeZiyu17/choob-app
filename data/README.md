# Recommendation data and handoff

## Current completed export

The supplied cleaned Yelp review sample has **484 reviews from 50 Philadelphia restaurants**. All restaurant IDs join to the supplied **5,855-row restaurant catalog**. Recommendations cover the 50 restaurants with sampled reviews, not all 5,855 catalog entries.

The completed run produced **835 validated review–dish mentions**, aggregated into **711 restaurant–dish pairs**. Of 484 reviews, 380 contain an extracted dish and 104 have no extracted dish. No reviews failed validation. Named drinks and ordered sides can also appear. Dish spelling/plural variants can remain separate.

Keep these three bundled files together from a single build:

| File | Purpose |
|---|---|
| `choob_recommendation_data.csv` | 711 aggregated restaurant–dish rows, taste descriptions and sentiment counts |
| `choob_dish_embeddings.npy` | 711 × 384 normalized float32 MiniLM vectors in exactly the CSV row order |
| `choob_recommendation_manifest.json` | Source/build hashes, actual extraction route, coverage, model revision and output hashes |

This run used **Codex-assisted annotations**, validated against exact source quotations, plus a small AI semantic audit and corrections. It did not execute Qwen or fine-tune weights. MiniLM actually generated the vectors locally. The manifest records `supplied_codex_annotations`; its Qwen token/retry settings are unused by this route. Quote matching and AI auditing do not replace human evaluation.

## Person 2 → Person 3: review input

Provide a UTF-8 `choob_reviews_sample.csv`, one complete review per row:

| Column | Meaning |
|---|---|
| `business_id` | Stable restaurant identifier |
| `restaurant_name` | Restaurant display name |
| `review_id` | Unique review identifier |
| `stars` | Original rating, 1–5 |
| `text` | Complete, nonempty review text used for extraction |

Use consistent restaurant IDs/names, no duplicate review IDs and no empty required fields. Include source, sample selection and cleaning notes. Keep review text and private checkpoints outside the public application folder. Review stars are preserved metadata; they are not assigned as the sentiment of every dish.

An optional `choob_restaurants.csv` provides `business_id`, `name`, `city`, `categories`, `stars` and `review_count`. The builder validates the join. A catalog alone cannot supply dish-level recommendations; adding review samples is how coverage grows.

## Rebuild

Install `requirements.txt`, then run from the project directory. `Choob_Recommendation_Pipeline.ipynb` contains the same builder and provides a Colab upload/download workflow.

For a new Qwen extraction (not the route used for the bundled output):

```bash
python build_recommendations.py --reviews /path/to/choob_reviews_sample.csv --restaurants /path/to/choob_restaurants.csv --work-dir /path/to/private-qwen-work --output-dir data
```

For a complete supplied annotation file:

```bash
python build_recommendations.py --reviews /path/to/choob_reviews_sample.csv --restaurants /path/to/choob_restaurants.csv --annotations /path/to/choob_annotations.jsonl --work-dir /path/to/private-annotation-work --output-dir data
```

The JSONL requires one object for every review, including reviews with no dishes: `{"review_id":"…","dishes":[]}`. Each dish has `dish_name`, exact `evidence`, `taste_tags` with exact evidence, a dish-level `sentiment`, and `sentiment_evidence`. See the builder prompt for the complete schema. Annotations and source reviews are required to reproduce this exact extraction; they are retained in the owner's private workspace rather than bundled here. Use a distinct private work directory for a changed source/configuration. Failed reviews remain explicit; inspect them and use `--retry-failures` where appropriate.

## Person 3 → Person 4 / Person 5

Person 4 keeps all three exports with the Flask app and installs the dependencies. The manifest prevents loading a mismatched CSV/vector pair and pins the query embedding model revision. No Qwen model is needed to serve the existing recommendations; serving uses MiniLM. The first model download needs internet unless its weights are cached.

Person 5 can run `python -m unittest discover -s tests -v` without weights, and `python evaluation/run_recommendation_smoke.py` with MiniLM available. Recorded results are in `evaluation/results/recommendation_smoke.json` and `recommendation_report.md`. Human relevance and extraction accuracy evaluation remains to be done.

Sampled historical reviews do not verify current menus, ingredient lists, dietary suitability, allergies or restaurant status. The app matches taste and rejects common explicit dietary/allergy requests. Ranking scores are not probabilities. No raw review text or evidence quotations are included in these exports.
