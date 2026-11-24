# Final Snap: fixed-image regression evaluation

Completed on November 24, 2026. This evaluates the real Flask `/api/recognize`
endpoint, using the final implementation and the same 72 photographs selected
for the November 16 rehearsal. It is a **same-image regression rerun**, not a
new, independent holdout or an estimate of overall real-world food accuracy.

## Results

All 72 requests returned HTTP 200. Strict and predeclared alias-aware scoring
gave the same aggregate values.

| Measure | Result |
| --- | ---: |
| Single-photo main-result Top-1 exact match | 40/60 (66.7%) |
| Single-photo reference present in the main result's three ranked choices | 55/60 (91.7%) |
| Single-photo primary output exactly matches the target set | 40/60 (66.7%) |
| Mixed-meal labeled targets found among primary dish suggestions | 11/26 (42.3%) |
| Mixed-meal photographs with every scored target found | 2/12 (16.7%) |
| Mixed-meal photographs with exactly the scored target set and no extras | 0/12 |
| Extra primary suggestions relative to scored mixed-meal targets | 9, across 7/12 photographs |

Top-three coverage measures whether the reference dish is available as an
alternative to one identification. It does **not** treat three alternatives
as three detected dishes, measure a user's selection success, or establish
91.7% automatic identification accuracy. First-choice exact match remains
66.7%. The Top-1 and mixed target-recall counts match the earlier same-image
rehearsal aggregates; no broad first-choice accuracy improvement is claimed.

Some visible accompaniments were expressly unscored in the original manifests.
Consequently, the nine extra suggestions are relative to those frozen scored
targets and must not be interpreted as exhaustive false-positive annotation
or full ground-truth precision. Source IDs, creators, licenses, target labels,
unscored items, input transformations and SHA256 values appear in the public
case manifest and in `protocol.json`.

## Version and environment

The executed checkout was **4be1cda19a19f2e4f893ff6ee6b75f945eb358c4**.
`remote_docs_equivalence.json` records a GitHub comparison showing that named
remote revision **97c44fde4a4cc9f03dea77f18dd111f2313e68f8** changes only
`README.md` and `TEAM_GUIDE.md`; executable code is identical between those
two revisions. This evaluation did not check out or execute 97c44fd.

CPU inference used four PyTorch threads, Python 3.12.14, PyTorch 2.14.1,
Transformers 4.57.6 and the cached official `openai/clip-vit-base-patch32`
model and processor. No model weights, recognition rules or confidence
thresholds were changed. The runner replaced only `get_clip` asset resolution
with that local pretrained cache. Model and processor were already downloaded.

`environment.json` records actual versions and model hashes. This was an
existing environment, not a clean reinstall: Pillow 13.0.0 exceeds the
repository's declared `pillow<13` range, although imports and all endpoint
requests completed successfully. Future exact reproduction should use the
recorded environment or explicitly report changed dependency versions.

The first endpoint call took 10.276 seconds, including recognizer/text-feature
setup. Across the 72 sequential requests, median test-client wall time was
0.658 seconds and mean was 0.811 seconds. These descriptive times exclude
model loading, network transfer, browser rendering and concurrent traffic;
they are **not production end-to-end latency benchmarks**.

## Reproduce from cached inputs

From the repository root, use an environment with the project dependencies.
Supply the two original evaluation directories and the official CLIP cache:

```bash
python evaluation/run_final_snap.py \
  --case-root "round1=/path/to/choob-rehearsal-evaluation-2026-11-16" \
  --case-root "round2=/path/to/choob-rehearsal-evaluation-round-2" \
  --assets "/path/to/snap_model_cache" \
  --output "/path/to/a/new/empty/final-snap-run"
```

Each supplied round directory contains `snap_images/`. The runner records the
actual checked-out commit for each new run. To enforce a particular revision,
add `--expected-commit` followed by that revision's full SHA; do not supply the
historical 4be1cda SHA when running a later checkout.
The recorded evaluation used the same command with `--expected-commit`
4be1cda19a19f2e4f893ff6ee6b75f945eb358c4, the existing project's
`recommendation-work/venv/bin/python`, and the two cached rehearsal directories.
The assets are not distributed in GitHub.

`--validate-only` checks case hashes, input availability, model assets and
runtime-source agreement with the checked-out commit, without loading a model
or running inference. The runner refuses a nonempty output directory and
freezes the protocol before model loading and predictions. Previously
completed evidence is not overwritten.

## Obtain inputs from source

Alternatively, create an external image root containing
`round1/snap_images/` and `round2/snap_images/`, then replace the two
`--case-root` arguments with:

```bash
--images-root "/path/to/external/image-cache" --download-images
```

This explicit option resolves the frozen Food-101 rows and Commons source
pages. Food-101 bytes are used unchanged. Commons originals are EXIF-oriented,
converted to RGB, resized proportionally to at most 1100 by 1100 pixels and
saved as JPEG quality 92, matching the original acquisition procedure.
JPEG encoder/source changes may produce a different hash. The runner stops
on a mismatch instead of silently accepting changed photographs; in that case
obtain the original cached images. Honor the image-level licenses and source
terms in the manifest. No source photographs or model weights are committed.

Without `--assets`, Transformers can resolve its existing local cache by the
official model ID; `--allow-model-download` separately enables network model
resolution. Image downloading and model downloading are explicit choices.

## Evidence files

- `protocol.json`: frozen scoring, sample references, source and runner hashes,
  and case manifest, written before inference.
- `predictions.json`: every complete API response and per-case scores.
- `predictions.csv`: compact case results with sources, hashes and timings.
- `summary.json`: counts, denominators, per-round results and timing scope.
- `environment.json`: actual dependencies and cached model hashes.
- `remote_docs_equivalence.json`: named-commit GitHub comparison.
- `runner_verification.json`: missing-input/hash-mismatch/output-preservation
  checks and independent recomputation from raw endpoint responses.

Frozen public cases: `evaluation/final_snap_cases_2026_11_24.json`.
Runner: `evaluation/run_final_snap.py`.
