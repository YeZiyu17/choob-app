# Choob CLIP baseline: automated photo evaluation

Run: 2026-10-22 21:48 PDT. Model: `openai/clip-vit-base-patch32` on CPU.

## Results

50 Food-101 validation photos were fetched automatically. Accuracy is calculated only on the 40 photos in the eight mapped categories below. The five generic ramen photos and five apple-pie photos are separate limitation cases.

| Measure | Result |
|---|---|
| Top-1 accuracy, mapped categories | 39/40 (97.5%) |
| Top-3 accuracy, mapped categories | 40/40 (100%) |
| Mean processing time, 50 photos | 0.268 s/photo |
| Median processing time | 0.265 s/photo |
| Separate model warm-up | 0.690 s |

| Dataset category | Choob label | Top-1 | Top-3 |
|---|---|---|---|
| dumplings | dumplings | 5/5 | 5/5 |
| fried_rice | fried rice | 4/5 | 5/5 |
| hamburger | hamburger | 5/5 | 5/5 |
| pad_thai | pad thai | 5/5 | 5/5 |
| pizza | pizza | 5/5 | 5/5 |
| spaghetti_bolognese | pasta | 5/5 | 5/5 |
| sushi | sushi | 5/5 | 5/5 |
| tacos | tacos | 5/5 | 5/5 |

## Observed errors and limitations

- Fried-rice row 4254 was ranked as shoyu ramen (relative score 0.6816415). Fried rice was second (0.1305536).
- All five generic ramen photos produced a ramen-family label. Food-101 does not annotate tonkotsu versus shoyu, so these do not establish subtype accuracy.
- All five apple-pie photos were forced into the existing candidate labels: dumplings, dumplings, dumplings, hamburger, pizza. The current model has no unknown-food rejection mechanism.
- Scores are relative softmax rankings among the ten candidates, not calibrated probabilities.
- Timing excludes image download and warm-up; it measures processing and inference, not Flask, upload, or browser response time.
- This is a small fixed subset across eight mapped categories, not the overall accuracy of the full ten-label model. Possible overlap with CLIP pretraining is unknown.

## Source and reproducibility

[Food-101 dataset](https://huggingface.co/datasets/ethz/food101) · [Original ETH Zurich description](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/).

The validation class blocks were located at fixed 250-row intervals using the public dataset viewer rows API. The first five rows in each predeclared class were selected and their dataset labels verified before inference. Selection was not changed after seeing predictions.

`food101_clip_results.json` contains every row ID, dataset label, mapped label, source image SHA-256, three predictions, and processing time. Source photos remain in the Colab session and are not included in this repository.

In the existing Colab session, load the original CLIP model and processor, then execute `evaluation/run_food101_clip.py` and call:

```python
summary, records = run_evaluation(model, processor, per_class=5)
```

The candidate list and image/text processing match the existing Flask `/api/recognize` baseline. This run does not verify the Flask route, UI, collection flow, Qwen model, or recommendation backend.
