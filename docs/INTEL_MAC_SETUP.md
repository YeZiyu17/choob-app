# Choob Intel Mac Installation, Startup, and Troubleshooting

Scope: Intel `x86_64` Macs running macOS and Python 3.11. This profile only addresses the Intel Mac incompatibility with `torch>=2.3`. Other platforms should continue to use `requirements.txt`; the Docker configuration has not been downgraded.

## 1. Clean installation

Run these commands from the repository root:

```bash
uname -m                     # Expected: x86_64
python3.11 --version         # Expected: Python 3.11.x
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-intel-mac.txt
python -m pip check
```

`pip check` should report `No broken requirements found.` The compatibility profile pins the core AI stack:

- `numpy==1.26.4`
- `torch==2.2.2`
- `transformers==4.44.2`
- `sentence-transformers==3.0.1`

Flask, Gunicorn, Pandas, Pillow, and Requests retain their tested major-version ranges.

## 2. Cache the models before the demo

Connect to a reliable network and run:

```bash
python cache_models.py
```

This command downloads and caches two public pretrained models:

- Image recognition: `openai/clip-vit-base-patch32` (CLIP ViT-B/32). The application adds prompt ensembles, synonyms, cached text features, and scope checking with the recorded threshold. The model weights were not fine-tuned.
- Text recommendation: `sentence-transformers/all-MiniLM-L6-v2`, pinned by the recommendation manifest to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The application compares query embeddings with saved vectors, then ranks with 85% semantic similarity and 15% smoothed dish sentiment. The model weights were not fine-tuned.

The application now checks the local cache first and uses the network only when the cache is missing. After caching, it can start without classroom Wi-Fi. Model caches must not be committed to Git.

## 3. Verify installation, tests, and real inference separately

Package installation, page availability, and successful model inference are three different checks.

```bash
# A. Package dependencies
python -m pip check

# B. 61 synthetic and integration regression checks (not model accuracy)
python -m unittest discover -s tests -v

# C. Real MiniLM inference, CSV/NPY/manifest alignment, and varied queries
python evaluation/run_recommendation_smoke.py

# D. Cache both models and start the server
python cache_models.py
python app.py
```

In another terminal, run:

```bash
curl http://127.0.0.1:7860/api/status
```

Finally, open `http://127.0.0.1:7860/` in a browser. Enter at least two clearly different English preferences in Discover and upload a photo in Snap. A working home page or a successful `pip check` alone does not prove model inference works.

## 4. Start and stop the application

For development or the classroom demo:

```bash
source .venv/bin/activate
python app.py
```

Open `http://127.0.0.1:7860/`. Keep the terminal running. Press `Ctrl+C` in that terminal to stop the server.

For a more production-like local launch:

```bash
source .venv/bin/activate
gunicorn -w 1 -b 127.0.0.1:7860 --timeout 180 app:app
```

Use one worker so that multiple workers do not each load their own copy of both models. Public deployment is not a prerequisite for the November 2 demo.

## 5. Troubleshooting

### `No matching distribution found for torch>=2.3`

Confirm that the machine is an Intel Mac and use `requirements-intel-mac.txt`. Do not modify the shared `requirements.txt` for every platform.

### The first request is slow

Model download, in-process model loading, and first inference are separate costs. Run `cache_models.py` in advance. After starting the application, make one Discover request and one Snap request to warm the process before recording.

### Hugging Face is contacted repeatedly while offline

Confirm that both model caches are complete. The current code tries `local_files_only=True` first and connects to the network only after a cache miss. If the cache is incomplete, reconnect and run `python cache_models.py` again.

### Port 7860 is already in use

Stop the older Choob server, or temporarily use another port:

```bash
PORT=7861 python app.py
```

### The API returns 503

- Snap 503: check the CLIP cache, available memory, and `recognition_config.json`.
- Discover 503: check the MiniLM cache and confirm that the CSV, NPY, and manifest in `data/` came from the same build and were not modified.
- Results metadata 503: confirm that the manifest exists and contains valid JSON fields.

### An image is rejected

The file must be a valid JPG, PNG, or WebP image, smaller than 8 MB, and no larger than 16 megapixels. An Unknown scope result is not a failed request; enter the actual dish name before collecting it.

## 6. Verification completed on November 1, 2026

- Machine: Quad-Core Intel Core i5, `x86_64`, macOS 26.7.1, Python 3.11.9.
- A new virtual environment was created under `/private/tmp`, and `requirements-intel-mac.txt` was installed from a clean environment. `pip check` passed.
- The same clean environment passed 61/61 regression checks, and both the home page and `/api/status` returned HTTP 200.
- Real MiniLM and CLIP inference both succeeded in the clean environment. The models were already cached, so download time was not measured.
- Recommendation artifact and model loading took approximately 80.43 seconds. The first MiniLM encode took approximately 1.43 seconds; the next two runs averaged approximately 0.013 seconds.
- CLIP model and prompt-cache construction took approximately 4.25 seconds. The first image inference took approximately 0.284 seconds; the next five runs averaged approximately 0.203 seconds.

The complete machine-readable result is in `evaluation/results/person4_clean_intel_benchmark_2026-11-01.json`. These timings are one local measurement, not a service-level guarantee.
