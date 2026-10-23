# Choob recognition v2 — frozen holdout comparison

The main improvement is scope handling: the recognizer can ask for manual input instead of assigning every photo to its menu. On 340 fixed holdout photos, unsupported-food false acceptance fell from 160/160 to 1/160. Supported-family Top-1 ranking improved by one photo, from 175/180 to 176/180. This improvement comes with reduced automatic coverage: 16/180 supported photos were marked uncertain.

Run: **23 October 2026, 11:44 PDT**, Google Colab CPU. Original weights: `openai/clip-vit-base-patch32`. Transformers 4.57.6, PyTorch 2.11.0+cpu. **No model weights were fine-tuned.**

## What changed

- Average four normalized text-prompt features per dish description and normalize the resulting prototype.
- Use synonyms and descriptions for nine supported families: ramen, sushi, dumplings, fried rice, pad thai, pizza, pasta, hamburger and tacos. Each family takes its most similar description.
- Merge the two ramen subtype labels into generic ramen. The available ground truth cannot validate tonkotsu/shoyu identification.
- Compete against 107 predefined background descriptions covering other foods and some non-food objects. The scope margin is the highest supported-family cosine similarity minus the highest background cosine similarity.
- Cache text features for subsequent photos. The pretrained image encoder stays unchanged.
- Return `status: uncertain`, `accepted: false`, `dish_name: Unknown` when the margin is below the calibrated threshold. Suggestions and relative scores remain available, but the UI leaves the editable dish name empty.
- Keep user confirmation for accepted predictions. Prevent stale photo requests from replacing newer results; discard old cuisine/category metadata when the user corrects a name.

This compares the complete inference pipeline. It does not isolate the contribution of each individual change.

## Predeclared sampling and calibration

Source: [ETHZ Food-101 validation](https://huggingface.co/datasets/ethz/food101), using the [dataset viewer rows API](https://huggingface.co/docs/dataset-viewer/rows).

All 600 rows were selected before inference, with their source labels checked. Image hashes and row identifiers are recorded. None overlap the previous 50-photo run by row or recorded image hash.

| Partition | Supported photos | Unsupported photos | Total |
|---|---:|---:|---:|
| Calibration | 9 families × 20 = 180 | 8 classes × 10 = 80 | 260 |
| Frozen holdout | 9 families × 20 = 180 | 16 classes × 10 = 160 | 340 |

Supported dataset classes: dumplings, fried_rice, hamburger, pad_thai, pizza, spaghetti_bolognese (mapped to pasta), sushi, tacos and ramen (family only).

Calibration unsupported classes: apple_pie, chocolate_cake, caesar_salad, french_fries, ice_cream, steak, pancakes and hot_dog. Holdout additionally includes baklava, cheesecake, chicken_wings, club_sandwich, cup_cakes, falafel, nachos and waffles. Those additional classes have no calibration photos, but their names are in the predefined background vocabulary; this is **not** an unseen-label generalization test.

Within each class, calibration uses offsets 20–39 for supported foods and 20–29 for unsupported foods. Holdout uses offsets 100–119 and 100–109 respectively. Failed downloads are retried without substituting a different image. No image was selected based on a prediction.

The threshold is the largest margin that retains at least 90% of the 180 calibration supported photos. This gives **0.004918932914733887**, accepting 162/180 calibration supported photos. It was frozen before holdout inference and was not adjusted after seeing holdout results. The shipped `recognition_config.json` includes the vocabulary fingerprint to detect stale calibration.

## Holdout results

| Measure | Original CLIP baseline | Optimized pipeline |
|---|---:|---:|
| Supported-family Top-1 ranking, before rejection | 175/180 (97.22%) | 176/180 (97.78%) |
| Supported-family Top-3 ranking, before rejection | 180/180 (100%) | 179/180 (99.44%) |
| Supported photos receiving an accepted suggestion | 180/180 (100%) | 164/180 (91.11%) |
| Correct among accepted supported photos | 175/180 (97.22%) | 162/164 (98.78%) |
| Correct and accepted / all supported photos | 175/180 (97.22%) | 162/180 (90%) |
| Unsupported photos incorrectly accepted | 160/160 (100%) | 1/160 (0.625%) |
| Unsupported photos marked uncertain | 0/160 | 159/160 (99.375%) |

Ramen is scored only at family level in both systems. On the eight non-ramen categories, Top-1 ranking is 156/160 (97.5%) versus 157/160 (98.125%); both have Top-3 160/160. Ramen family Top-1 is 19/20 for both, and Top-3 is 20/20 versus 19/20.

The optimized pipeline rejects 16 supported photos: 14 of these had a correct first suggestion. Those photos require manual input. The one extra correct Top-1 ranking, a hamburger photo, is also rejected, so the raw ranking gain does not translate into an extra automatically accepted correct result.

### Remaining accepted errors

| Source label | Food-101 row | Accepted suggestion |
|---|---:|---|
| fried_rice | 4365 | pad thai |
| hamburger | 857 | tacos |
| nachos (unsupported) | 19104 | tacos |

The nachos error still has a 99.728% relative ranking score. **Relative scores are not calibrated correctness probabilities.** User confirmation remains necessary.

## Integration and timing checks

The actual Flask route was exercised through Flask's test client with real downloaded image bytes:

- Supported dumplings photo: HTTP 200, accepted suggestion, confirmation required.
- Unsupported apple pie: HTTP 200, uncertain, Unknown dish/cuisine/category, manual entry required.
- Missing upload and corrupt image: HTTP 400.
- Cached baseline Top-3 scores matched direct CLIP forward on one photo, with a maximum absolute difference of approximately 2.15 × 10⁻¹⁰.
- Four local policy regression checks passed, including a high relative score failing scope checking and stale vocabulary configuration being rejected.
- JavaScript event checks covered manual corrections, placeholder names, interleaved photo requests and failed requests clearing older results. These are event-level checks, not a complete browser upload/deployment test.

On a separate **five-photo timing check** with the same warm CPU model, mean processing was 0.348 seconds for the original path and 0.204 seconds for the cached optimized path. The baseline ran first for each photo. These timings exclude startup, downloads, network and Flask; five photos do not establish production latency. The main 600-photo comparison shares image features between both systems and its batched encoding time must not be presented as separate per-system latency.

## Files and handoff

- `recognition.py`: reusable recognizer and fixed prompt vocabulary.
- `recognition_config.json`: frozen calibration threshold; ship with the exact recognizer.
- `app.py`, `index.html`: backend and user-confirmation integration.
- `evaluation/run_clip_comparison.py`: complete sampling, calibration and holdout runner.
- `evaluation/results/clip_comparison.json`: all 600 source records, rankings, decisions and metrics.
- `evaluation/results/api_smoke.json`: real endpoint check responses, versions and timing values.
- `evaluation/results/frozen_calibration.json`: original calibration artifact written before holdout inference.
- `evaluation/results/sample_manifest.json`, `sampling_plan.json`: original selection plan and all 600 source records before predictions.
- `Choob_Recognition_Optimized.ipynb`: clean Colab reproduction entry point; code outputs start empty and its introductory summary is the recorded run above.

Person 4 should keep the configuration alongside the recognizer when deploying the Flask app. An uncertain response must leave the dish name for user entry; it must not be automatically collected as Unknown. Live restaurant recommendations still require the two original exported data files described in `data/README.md`; this recognition change does not regenerate them.

## Limits

This is a fixed Food-101 subset, not a representative estimate of real user accuracy. The image labels are independent of model predictions, but possible overlap with CLIP pretraining is unknown. All 600 photos are food: non-food objects, mixed dishes and phone-camera conditions were not validated in this comparison. Background vocabulary helps scope decisions but cannot guarantee rejection of every unsupported image. Broader pasta variants also need separate evaluation.

Implementation reference: [OpenAI CLIP prompt engineering notebook](https://github.com/openai/CLIP/blob/main/notebooks/Prompt_Engineering_for_ImageNet.ipynb). Dataset details: [ETH Zurich Food-101](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/). CLIP limitations: [official model card](https://huggingface.co/openai/clip-vit-base-patch32#limitations).
