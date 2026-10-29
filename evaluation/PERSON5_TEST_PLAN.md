# Person 5 — testing the updated Choob prototype

1. Pull the latest main and follow TEAM_GUIDE.md. Run Flask locally. Open Snap → View evaluation results and record the current build ID/date.
2. Use `results/recommendation_human_review.csv`: it contains 15 frozen preferences × 5 actual results × two versions. Fill `human_relevant_yes_no` and `human_reason`; keep all system/query/rank fields unchanged. Decide relevance from the stated preference, not from the model score. Record uncertain judgments explicitly.
3. Predefine how uncertain ratings count, then report relevant results / five for each query and the mean across queries for each version. Include counts and disagreements; do not describe larger coverage or successful requests as relevance accuracy.
4. Try the same preferences through Discover and record errors/confusing steps, response times and screenshots. Test empty input and the unsupported dietary request. Try Snap upload → correction/confirmation → Collect, then Discover → Collect and browser persistence.
5. For extraction accuracy, obtain private review samples from Person 2/3 and independently label actual dishes and dish sentiment before comparing with AI annotations. The existing AI spot checks are not human gold labels.
6. Return the completed sheet, tested build ID, bug cases (input, expected, actual), and screenshots. If data/model settings change afterward, rerun the affected cases under the new version.

Reproduce the model/data comparison from the project root (provide the archived v1 data privately):

```bash
python evaluation/run_recommendation_comparison.py --baseline-dir /private/v1/data --baseline-report evaluation/results/recommendation_baseline_v1.json --output /private/recommendation_comparison.json --human-output /private/recommendation_human_review.csv
```

The source catalog has 5,855 rows but only sampled review coverage is recommendable. Reviews are historical; menus, business status and dietary suitability are unverified. Scores are uncalibrated rankings. UI community/sample restaurant panels remain illustrative.
