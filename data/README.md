# Dataset exports required for live recommendations

## Person 2 → Person 3: review input

Person 2 supplies a cleaned, real-review CSV, preferably named `choob_reviews_sample.csv`. The existing notebook expects these exact five columns:

| Column | Meaning |
|---|---|
| `business_id` | Stable restaurant identifier |
| `restaurant_name` | Restaurant display name |
| `review_id` | Unique review identifier |
| `stars` | Original review star rating |
| `text` | Complete, nonempty review text; this is the model input |

Use UTF-8, one review per row, consistent restaurant IDs/names, and no duplicate review IDs or empty/whitespace-only text. Include a short note describing the source, number of restaurants/reviews and cleaning steps. The previous notebook recorded 484 rows in this format; the new file need not contain exactly that count.

Person 3 uses the notebook to extract dish names, taste tags and dish-level sentiment, aggregate restaurant–dish records, and generate embeddings. Review stars are preserved metadata, not the sentiment of every dish in that review. If the team has an existing `choob_dish_database.csv`, it can be used to resume from the dish-processing stage.

## Person 3 → Person 4: recommendation output

Run the relevant processing and **final export cell (cell 43)** in `Choob_AI_Dish_Recognition.ipynb`, then download and place both files in this directory:

1. `choob_recommendation_data.csv`
2. `choob_dish_embeddings.npy`

Export both from the **same notebook run** to keep rows aligned. The backend will show a descriptive error if either file is missing. Do not substitute the sample HTML recommendations or fabricated rows and call them AI results.

The third exported file (`choob_recommendation_results.csv`) is for reference, not used for live inference.

Check the source dataset's licensing and whether publishing derived review data is permitted before making this repository public.
