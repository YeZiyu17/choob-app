# Choob – Data Notes (v2, review augmentation)

## Source
- **Yelp Open Dataset**, JSON release downloaded from https://business.yelp.com/data/resources/open-dataset/ (archive files dated 2022-01-19; reviews span 2005–2022).
- Full archive: 150,346 businesses and 6,990,280 reviews. Philadelphia: 14,569 businesses.
- Used under the Yelp Dataset License (academic / non-commercial use).
- Only `yelp_academic_dataset_business.json` and `yelp_academic_dataset_review.json` were read.

## Scope
- **Restaurant universe:** the team's existing `choob_restaurants.csv`, which lists 5,855 Philadelphia businesses tagged *Restaurants*. All reviews in this release come from these restaurants, so every `business_id` in the review file joins to the restaurant file.
- **Raw review pool:** 687,553 reviews belonging to those 5,855 restaurants.

## Sampling
v1 had 484 reviews from 50 randomly chosen restaurants (5–10 reviews each). v1 is kept unchanged and v2 adds to it in two ways.

**A. More reviews for the 50 existing restaurants.**
- Each restaurant was topped up to at most 40 reviews.
- Many of these restaurants have few reviews on Yelp, so 5 of them got no new reviews and the per-restaurant median is now 26.5 (range 5–40).

**B. Restaurants for cuisines the v1 test set under-covered.**
- Each restaurant got a primary cuisine group based on its Yelp categories, for example Thai, Vietnamese or Ethiopian/African.
- Specific cuisine tags take priority over broad ones, so a restaurant tagged "Thai, Chinese" counts as Thai.
- v1 had 0–3 restaurants in most non-American cuisines. Every such group was filled up to 6 restaurants, with 30 reviews per new restaurant.
- Groups that were already well covered were not topped up: Mexican, Italian/Pizza, breakfast/diner/cafe, cheesesteaks/sandwiches, and American/burgers/bars.
- Rules for a candidate restaurant:
  - It is currently open (`is_open = 1`) and has at least 40 Yelp reviews.
  - Its tags point to one cuisine only.
  - It has none of these secondary-concept tags: Pizza, Chicken Wings, Fast Food, Burgers, Salad, Steakhouses, Pubs, Wine Bars, Hookah Bars and similar.
  - For BBQ, it is also not tagged American (New), Breakfast & Brunch or Sandwiches. For Vegan/Vegetarian, it must carry the *Vegan* tag.
- Picks were spread across rating tiers (below 3.5, 3.5–4, 4.5 and up).

**How reviews were chosen (A and B).**
- Reviews that mention a dish were chosen first, using a lexicon of about 140 dish terms (pho, injera, bibimbap, brisket, and so on). Choob extracts dish-level opinions, and 96% of the added reviews name at least one dish.
- Order within each group was otherwise random. Random seed: 586.

## Cleaning steps
1. Whitespace normalized: runs of spaces/tabs collapsed, 3+ newlines reduced to 2, text trimmed. The wording was not changed. This also applies to the 484 v1 texts (165 had extra spaces).
2. Reviews shorter than 50 characters or longer than 5,000 characters were dropped.
3. Non-English reviews were dropped (less than 90% ASCII letters).
4. Reviews whose star rating is not one of 1–5 were dropped.
5. Independence rules:
   - Every `review_id` is new, so no review already in v1 is repeated.
   - No duplicate text within a restaurant.
   - One review per user per restaurant (the most recent one is kept).
6. `restaurant_name` is set from the restaurant table, so each ID has one canonical name.
7. In the restaurant table, `city` was trimmed and title-cased; 3 rows had spelled "philadelphia" in lowercase or with a trailing space.

Reviews removed among the candidates scanned:

| Reason | Reviews removed |
|---|---|
| Same user, same restaurant | 534 |
| Duplicate text | 27 |
| Too short | 14 |
| Non-English | 5 |
| Already in v1 | 484 |

Known v1 issue (kept as is): 4 pairs of v1 reviews are written by the same user for the same restaurant.

## Counts before and after

| | v1 (before) | v2 (after) |
|---|---|---|
| Reviews in `choob_reviews_sample.csv` | 484 | **3,526** |
| Restaurants with reviews | 50 | **123** |
| Rows in `choob_restaurants.csv` | 5,855 | 5,855 (123 flagged `in_review_sample`) |
| Cuisine groups with at least 6 restaurants | 4 | 19 |
| Mean star rating of reviews | 3.52 | 3.80 |

Where the new reviews come from:
- 852 are new reviews for 45 of the existing restaurants.
- 2,190 come from 73 new restaurants.

## Files
- **`choob_reviews_sample.csv`** – columns: `business_id`, `restaurant_name`, `review_id`, `stars`, `text` (full review), `user_id`, `date`, and `sample_group`.
  - `sample_group` is `original`, `added_existing_restaurant` or `added_new_cuisine`. Filter on `original` to reproduce the v1 test set.
- **`choob_restaurants.csv`** – the original columns (`business_id`, `name`, `city`, `categories`, `stars`, `review_count`) plus:
  - `cuisine_group`
  - `is_open`
  - `in_review_sample`
  - `sample_review_count`: number of reviews for that restaurant in the sample file
- **`run_log.json`** – machine-readable counts from the run.
- **Scripts** (`scripts/`):
  - `prefilter.sh` pulls the Philadelphia restaurant rows out of the Yelp archive in one pass.
  - `choob_augment.py` does the sampling and cleaning.
  - The whole run is reproducible with the fixed seed.

## Limitations
- Philadelphia only. The Yelp Open Dataset does not cover Los Angeles.
- Reviews end in January 2022, so some restaurants may have closed since then. `is_open` reflects the 2022 snapshot.
- Cuisine groups come from Yelp's self-reported tags. A few picks may still be loose fits.
- Picking dish-mentioning reviews first makes the sample more "dish-dense" than Yelp overall. It is good for training the dish extractor, but not a neutral sample of opinions.
- Star ratings skew positive (42% are 5-star), as on Yelp in general.

## Integration audit (28 Oct 2026)

The three supplied files were independently checked before rebuilding recommendations:

- 3,526 unique review IDs; 123 restaurants with sampled reviews; 5,855 catalog rows.
- No missing required review values, invalid star ratings, duplicate review text, unmatched business IDs or conflicting restaurant names.
- All 484 original review IDs remain. In 165 texts, only whitespace changed; old annotation quotes were migrated with the same whitespace rule and revalidated as exact substrings.
- 19 of 21 primary cuisine groups contain at least six sampled restaurants. American/Burgers/Bars has four and Other has two; the broad groups were not expansion targets.
- Four same-user/same-restaurant pairs from the original data remain. Dish support counts use distinct review IDs, so these counts should not all be described as independent reviewers.
- Twenty sampled restaurants have `is_open=0` in the historical snapshot. Reviews span 10 Sep 2006 to 19 Jan 2022; neither the open flag nor these reviews establish current operating status or menus.
- The referenced raw-data scripts and `run_log.json` were not included in the three-file handoff. Input validation was reproduced; the complete sampling process from the raw archive was not rerun.

The raw review CSV and private source quotations remain outside the public app package. Restaurant metadata used in dish descriptions is a cuisine signal, not verification of ingredients or dietary suitability.
