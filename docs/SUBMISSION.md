# Final documentation submission

Submit the seven-page [English technical report](Choob_Technical_Report_Final.docx), this public `final` repository, and the documented local application route. The verified platform is macOS ARM64 with Python 3.12.14. Keep a network connection available; live Discover requires your own Gemini and Tavily keys. A hosted application is not claimed for this chosen local route.

## Requirement mapping

Page numbers refer to the English report. Six body pages plus one references page are within the required 5–7 pages.

| Guideline | Location | Coverage |
| --- | --- | --- |
| 7.1 Problem | Page 1 | Challenge, users and reason for AI |
| 7.1 Architecture | Pages 1–2 | Figure, data flow, UI/model components, decisions and alternatives |
| 7.1 Data and model | Pages 2–3 | Provenance, processing, model settings, no fine-tuning and reproducibility limits |
| 7.1 Evaluation | Pages 4–6 | Quantitative baseline/regression, fresh Discover results, failures and timing scope |
| 7.1 Lessons and future work | Page 6 | What worked, what failed and next steps |
| 7.1 References | Page 7 and register below | Research, data, image credits, models, software, services and tools |
| 7.2 Repository | README, TEAM_GUIDE, requirements and modules | Setup, usage, structured code and explanatory comments |
| 7.3 Working application | README and verification below | Independent dependency installation, local HTTP startup and real model smoke checks on the recorded platform |

## Evaluation versions and interpretation

Quantitative Snap evaluation executed application commit `4be1cda19a19f2e4f893ff6ee6b75f945eb358c4`. Its [frozen evaluation archive](https://github.com/YeZiyu17/choob-app/tree/4ebda3596cc6898f698912df553d87346e9fe5d2/evaluation) is published at `4ebda35`.

- [Snap](../evaluation/results/final_snap_2026_11_24/README.md): 40/60 exact single-dish Top 1; 55/60 target present among Top 3; 11/26 primary mixed-meal targets; 2/12 mixed photos with all targets found. The 72 photos are known regression inputs. Top 3 coverage is not automatic accuracy.
- [Discover](../evaluation/results/final_discover_2026_11_24/README.md): 12/12 fresh requests returned 25 cards. The AI-assisted source audit passed 20/25, failed 2/25 and found insufficient evidence for 3/25. It is not a blinded human study and does not reconstruct the lost presentation logs.
- Submission setup checks are separate from those quantitative experiments. No recognition weights, prompts, thresholds or ranking logic were changed by this submission review.

## Local setup verification

See the [verification record](../evaluation/results/submission_check_2026_11_24/README.md), [machine-readable smoke results](../evaluation/results/submission_check_2026_11_24/submission_smoke.json) and [platform dependency lock](../requirements-macos-arm64-py312-verified.txt). The [full regression run](../evaluation/results/submission_check_2026_11_24/regression-tests.txt) passed all 134 tests.

An independent Python 3.12.14 virtual environment installed the declared requirements without inheriting system/user site-packages, and `pip check` passed. The application checks cover local HTTP startup, routes/assets, malformed inputs, local recommendation inference, missing-key behavior and three representative Snap photos. Raw suggestions include extra dishes; these are integration smoke checks, not a new accuracy study. Public model assets were reused, so first-time downloads were not tested. No new live Discover requests were made.

Windows, Intel Mac, Docker construction, hosted deployment and physical-device behavior were not verified by this backend check. Follow the README's network-connected local route. Optional Docker examples are separate and are not the evidence used for the local submission.

The annotation-rebuild notebook now saves and checks all four named private inputs, including `annotation_provenance.json`; the upload regression is tested. The full private-data rebuild was not rerun. The historical recognition notebook reproduces the older nine-family experiment, not the final multi-dish application.

## Resource register

The report lists principal papers/data and all twelve mixed-meal image credits. This register adds the implementation resources used or discussed. Transitive package versions are recorded in the verified lock. Optional providers are identified separately from the final campaign.

| Resource | Role and primary reference |
| --- | --- |
| CLIP | Pretrained image/text matching; [paper](https://proceedings.mlr.press/v139/radford21a.html), [model](https://huggingface.co/openai/clip-vit-base-patch32) |
| Food-101 | Evaluation images; [dataset/paper](https://data.vision.ee.ethz.ch/cvl/datasets_extra/food-101/), [mirror](https://huggingface.co/datasets/ethz/food101) |
| Wikimedia Commons | Mixed photos; individual URLs/authors/licenses in report reference 9 and [manifest](../evaluation/final_snap_cases_2026_11_24.json) |
| Yelp Open Dataset | Historical reviews/metadata; [dataset](https://business.yelp.com/data/resources/open-dataset/), [sampling and cleaning](../data/DATA_NOTES.md) |
| MiniLM and Sentence Transformers | Local embeddings; [pinned model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41), [library](https://www.sbert.net/) |
| Gemini and Tavily | Final live-menu interpretation/retrieval; [Gemini](https://ai.google.dev/gemini-api/docs/structured-output), [Tavily](https://docs.tavily.com/documentation/api-reference/endpoint/search) |
| MLX-LM and Qwen2.5-1.5B-Instruct-4bit | Separate optional local chat worker; [MLX-LM](https://github.com/ml-explore/mlx-lm), [model](https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit) |
| Qwen2.5-VL-3B-Instruct | Earlier exploration, not integrated into Snap; [model](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct) |
| PyTorch, Transformers, Hugging Face Hub, safetensors | Inference and asset loading; [PyTorch](https://docs.pytorch.org/docs/stable/index.html), [Transformers](https://huggingface.co/docs/transformers/index), [Hub](https://huggingface.co/docs/huggingface_hub/index), [safetensors](https://huggingface.co/docs/safetensors/index) |
| Flask and Gunicorn | App/deployment server; [Flask](https://flask.palletsprojects.com/en/stable/), [Gunicorn](https://docs.gunicorn.org/en/stable/) |
| NumPy, pandas, Pillow, Requests | Arrays, tables, images and HTTP; [NumPy](https://numpy.org/doc/stable/), [pandas](https://pandas.pydata.org/docs/), [Pillow](https://pillow.readthedocs.io/en/stable/), [Requests](https://requests.readthedocs.io/en/latest/) |
| Leaflet 1.9.4, OpenStreetMap, Nominatim | Maps and reverse geocoding; [Leaflet](https://leafletjs.com/reference-1.9.4.html), [OSM attribution](https://www.openstreetmap.org/copyright), [Nominatim](https://nominatim.org/release-docs/latest/api/Reverse/) |
| Google Maps JavaScript API | Optional browser map; [key setup](https://developers.google.com/maps/documentation/javascript/get-api-key). This browser key is delivered to the client and should be origin-restricted. |
| Nunito | Interface font; [project](https://github.com/googlefonts/nunito), [bundled OFL notice](../static/fonts/OFL-Nunito.txt) |
| OpenAI Codex | Assisted annotation, implementation and documentation; [Codex](https://openai.com/codex/), [annotation notes](../data/README.md). Exact historical annotation runtime version was not recorded. |
| OpenAI web search and Firecrawl | Optional alternative Discover providers, not the final campaign; [OpenAI](https://platform.openai.com/docs/guides/tools-web-search), [Firecrawl](https://docs.firecrawl.dev/features/search) |
| Python, Google Colab, GitHub, Docker | Runtime/workflow/optional packaging; [Python](https://docs.python.org/3.12/), [Colab](https://colab.research.google.com/), [GitHub](https://docs.github.com/), [Docker](https://docs.docker.com/) |
| Canva | [Final presentation](https://www.canva.com/design/DAHbs-Eg1bc/qO4EzX5zm1DNHkNq2uReKQ/edit) |

## Remaining limits and handoff

No structured human usability study, independent annotation-accuracy study, new-user photo generalization result, production-load benchmark or billed API-cost measurement is available. The original Discover model override was not independently inspected. Private Yelp source and annotation inputs are needed to rebuild the historical export. These limits are disclosed in the report; measurements have not been invented to fill them.

Hand in the English report through the course's designated channel and include the public repository URL and local-run instructions. GitHub hosts the source; the application requires a running backend.
