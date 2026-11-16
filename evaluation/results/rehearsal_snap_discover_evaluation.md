# Choob rehearsal evaluation

November 16, 2026 · Build [`3725948`](https://github.com/YeZiyu17/choob-app/commit/37259485b5eff73143f71c72eb5917f6a8a2af52)

We tested Snap's expanded food recognition and Discover's live menu recommendations twice on the same build.

## Snap

In each round, we sent 30 single-dish photos and six mixed-meal photos through the app's recognition endpoint using the same CLIP ViT-B/32 weights and scoring rules. We selected three Food-101 validation photos per round from each of 10 categories outside the original nine, using fixed offsets (173–175 in round one and 176–178 in round two). The two rounds used distinct images. We chose the visible target dishes in each mixed meal before running recognition on the unedited Wikimedia Commons photos. [Food-101 dataset](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/) · [Wikimedia Commons](https://commons.wikimedia.org/)

| Measure | Round 1 | Round 2 | Combined |
| --- | ---: | ---: | ---: |
| Single-dish photos with an exact match | 20/30 (66.7%) | 20/30 (66.7%) | 40/60 (66.7%) |
| Labeled dishes found in mixed meals | 6/14 (42.9%) | 5/12 (41.7%) | 11/26 (42.3%) |
| Mixed-meal photos with every labeled dish found | 1/6 | 1/6 | 2/12 |

Single-dish accuracy held steady across the two samples. Snap missed the waffle label in all six waffle photos. Both photos of a burger and fries returned the two target dishes plus an extra suggestion for yuca fries. In round two, Snap identified pizza in a pizza-and-salad photo and missed the salad. The single-dish result covers the 10 selected categories. Mixed-meal coverage counts dishes labeled before testing.

**Next step.** Test whether scoring regions around individual dishes recovers more of the labeled dishes without increasing extra suggestions. Keep the user review step in place so users can correct suggestions and add missed dishes before saving.

## Discover

We sent the same nine requests in four cities through the live Tavily search and Gemini recommendation flow in each round. We compared every returned card with its linked menu or a corroborating merchant menu. A pass required evidence for the dish, current venue and city, cuisine, and any flavor, region or named dish the user requested. We recorded contradictions and insufficient evidence separately.

| Measure | Round 1 | Round 2 | Combined |
| --- | ---: | ---: | ---: |
| Requests returning at least one recommendation | 6/9 | 5/9 | 11/18 |
| Requests returning no recommendations without an error | 2 | 1 | 3 |
| Requests returning a Gemini-related HTTP 503 error | 1 | 3 | 4 |
| Recommended cards passing all applicable checks | 9/15 (60.0%) | 8/11 (72.7%) | 17/26 (65.4%) |
| Cards that failed a check | 3 | 1 | 4 |
| Cards with insufficient evidence | 3 | 2 | 5 |

Philadelphia’s Italian and crispy request returned two verified recommendations in both rounds. Los Angeles’s Hunan and spicy request returned no cards in either round. A Chicago recommendation passed the dish-name check against a historical menu, and the address is now listed by another venue. The second round had a higher share of verified cards and fewer requests that returned recommendations. The combined figures describe these two runs and include repeated requests and cards. [Current venue at the Chicago address](https://apothecary-lounge.com/contact/)

**Next step.** Improve recovery from temporary Gemini errors and strengthen checks that menu sources are current and support what the user asked for. Track the share of requests that return recommendations separately from the share of cards that pass the audit.
