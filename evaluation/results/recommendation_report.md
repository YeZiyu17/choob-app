# Recommendation update report — 29 Oct 2026

## Data and actual method

The three supplied v2 files were checked: 3,526 unique review IDs, 123 sampled restaurants, 5,855 catalog rows, no missing required fields, invalid ratings, duplicate review text or broken restaurant joins. All 484 original IDs remain; 165 source texts changed only whitespace. The previous 835 dish annotations were migrated with that same whitespace rule and revalidated.

Added reviews use explicit Codex-assisted annotation with exact source quotation validation, followed by an independent AI spot check. Local Qwen pilots were evaluated during development but were not used for this export. No weights were fine-tuned. Real pinned MiniLM inference generated a **5,993 × 384 float32** normalized matrix. Supplied cuisine groups now participate in dish descriptions; the scoring formula is unchanged at **0.85 cosine similarity + 0.15 smoothed dish sentiment**.

| Objective coverage/support measure | v1 | v2 |
|---|---:|---:|
| Reviews processed | 484 | 3,526 |
| Restaurants represented | 50 | 123 |
| Restaurant–dish pairs | 711 | 5,993 |
| Review–dish mentions | 835 | 8,667 |
| Pairs with at least two supporting reviews | 84 | 1,141 |

Current statuses: 3,165 reviews with extracted dishes, 361 with no extracted dish, 0 unresolved failures. These are processing/coverage counts, not accuracy or proof that extraction found every dish.

## Completed checks

- **54 regression tests passed** using synthetic fixtures, covering evidence validation, source-bound provenance, paired artifacts, API behavior and dynamic Results metadata. This is program correctness, not model accuracy.
- **5 real MiniLM + Flask smoke requests succeeded**, with 5 distinct top-five lists. Regenerated-row maximum vector difference: `0.0`. Full output hashes match the manifest.
- **15 fixed preference probes** ran against the archived v1 and current datasets using the same real query vectors and fixed scoring formula. 15 top-five orders changed. Added coverage or changed rankings do not establish improved relevance.
- Both versions passed the evaluator's seven malformed/unsupported-request cases. Actual query responses and descriptive timings are in `recommendation_comparison.json`; the real current loader is exercised separately by `recommendation_smoke.json`.
- Actual local HTTP checks passed for current build metadata, a new-cuisine preference, empty input, an unsupported allergy request and one real CLIP image inference. See `local_http_smoke.json`; this does not establish image accuracy or browser-flow completion.
- Human relevance labels are deliberately blank in `recommendation_human_review.csv`. Human evaluation is **pending**.

Read the machine-readable reports for exact version hashes and timing scope. Test-client timings exclude startup, loading, network and browser rendering; single requests are not a controlled latency benchmark. Archived v1 evidence remains in `recommendation_v1_report.md`, `recommendation_v1_smoke.json` and `recommendation_baseline_v1.json`.

## Limits and next evaluation

These are dish-dense, historically sampled Philadelphia reviews, not current menus or a representative sample of all opinions. Four old same-user/restaurant pairs remain; twenty sampled restaurants were closed in the 2022 snapshot. Named drinks/sides and spelling variants remain. Cuisine and taste matching do not verify ingredients, diets or allergies; common explicit dietary requests return HTTP 422. English preference relevance needs human assessment.

Person 5 should complete the fixed preference sheet, independently label extraction and sentiment on private source reviews, record incorrect/uncertain cases and check the full UI flow. Numerical human relevance/accuracy claims must wait for that work. This local app is not a shared hosted deployment.
