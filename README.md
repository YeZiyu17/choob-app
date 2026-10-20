# Dataset exports required for live recommendations

Ask the colleague who authored `Choob_AI_Dish_Recognition.ipynb` to run its **final export cell (cell 43)**, then download and place both files in this directory:

1. `choob_recommendation_data.csv`
2. `choob_dish_embeddings.npy`

Export both from the **same notebook run** to keep rows aligned. The backend will show a descriptive error if either file is missing. Do not substitute the sample HTML recommendations or fabricated rows and call them AI results.

The third exported file (`choob_recommendation_results.csv`) is for reference, not used for live inference.

Check the source dataset's licensing and whether publishing derived review data is permitted before making this repository public.
