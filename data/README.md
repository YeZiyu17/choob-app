# Recommendation data and handoff

## Current export — 29 Oct 2026

The supplied v2 input has **3,526 reviews from 123 Philadelphia restaurants**. All IDs join to the **5,855-row catalog**. Recommendations cover **123 restaurants**, rather than the full catalog.

The completed build has **8,667 evidence-backed review–dish mentions** and **5,993 restaurant–dish pairs**. There are **3,165 reviews with extracted dishes**, **361 with no extracted dish**, and **0 unresolved processing failures**. An empty dish result is not a failure or proof that no dish was missed. Named drinks and separately consumed sides can appear. Spelling/plural variants may remain separate.

| Keep these files together | Actual contents |
|---|---|
| `choob_recommendation_data.csv` | 5,993 dish rows, source cuisine/city metadata, exact-row-order descriptions and sentiment counts |
| `choob_dish_embeddings.npy` | 5,993 × 384 normalized float32 MiniLM vectors |
| `choob_recommendation_manifest.json` | Source/build/annotation hashes, actual extraction route, counts, fixed model revision and output hashes |

The build uses **Codex-assisted annotations**: 484 old records were whitespace-migrated and revalidated; 3,042 added reviews were explicitly annotated from their complete source texts. Every retained dish and taste quote is validated as an exact source substring. Dish sentiment is separate from the restaurant's star rating. Qwen experiment outputs are not included. MiniLM embedding inference actually ran locally; **no weights were fine-tuned**. AI annotation and AI spot checks do not replace human evaluation.

The fixed MiniLM revision is `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Descriptions combine dish names, explicit taste evidence and the supplied restaurant cuisine group. Ranking stays 85% cosine similarity and 15% smoothed dish sentiment. Scores are not probabilities, and cuisine metadata is not a verified ingredient/diet filter.

## Person 2 → Person 3 inputs

Provide UTF-8 `choob_reviews_sample.csv`, one complete review per row, with `business_id`, `restaurant_name`, `review_id`, `stars` (1–5), and nonempty `text`. Extra `user_id`, `date` and `sample_group` metadata are allowed. Use consistent restaurant IDs/names, unique review IDs, and include source, selection and cleaning notes. The optional restaurant CSV has `business_id`, `name`, `city`, `categories`, `stars`, `review_count`; v2 adds `cuisine_group`, historical `is_open`, `in_review_sample` and `sample_review_count`.

Read [DATA_NOTES.md](DATA_NOTES.md) for the supplied sampling notes and independently checked exceptions. The raw reviews, user IDs, annotation JSONL and source quotations remain private, outside the public app folder.

## Rebuild the recorded annotation export

Install `requirements.txt`. Obtain the same private inputs, complete annotation file and matching provenance JSON from Person 3. Use a fresh private work directory for changed inputs/settings:

```bash
python build_recommendations.py --reviews /private/choob_reviews_sample.csv --restaurants /private/choob_restaurants.csv --annotations /private/choob_annotations.jsonl --annotation-provenance /private/annotation_provenance.json --work-dir /private/choob-v2-build --output-dir data
```

The notebook embeds the same builder for Colab CPU export. Every review must have exactly one JSONL object `{"review_id":"…","dishes":[]}`, including zero-dish results. Dishes carry an exact name/quote, dish-level sentiment and its evidence, and any explicitly supported taste tags. Missing, duplicate, unexpected or unresolved failed records stop the build. The provenance source hash and review counts must match the CSV. Exact annotation/source files are needed to reproduce this recorded extraction; they are not bundled publicly.

## Person 3 → Person 4 / Person 5

Person 4 keeps all three export files together and **restarts Flask after replacing data**, so an old cached recommender cannot coexist with new statistics. The loader checks hashes and dimensions and pins the embedding-model revision. `.gitattributes` preserves CSV/NPY bytes across operating systems so Git cannot silently change a hash-checked export. Serving and annotation export need CPU; Qwen is not needed to run the app.

Person 5 uses `evaluation/results/recommendation_human_review.csv` and the fixed 15-query comparison. The CSV contains actual baseline/current responses and intentionally blank human relevance/reason fields. See `evaluation/PERSON5_TEST_PLAN.md`. Run `python -m unittest discover -s tests -v`, `python evaluation/run_recommendation_smoke.py`, and the comparison command in that plan.

Historical reviews span 2006–2022. Twenty sampled restaurants were closed even in that snapshot. Four original same-user/same-restaurant pairs remain, so review counts mean distinct review IDs rather than entirely independent people. Current menus, operating status, ingredients, allergies and dietary suitability are unverified. Human recommendation relevance and extraction-accuracy evaluation remain pending.
