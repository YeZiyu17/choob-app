# Final Discover evaluation on November 24 2026

This is a new live evaluation, not a reconstruction of the unavailable final-presentation logs.
The query suite was frozen before inference: the nine historical cases plus three San Francisco
cases, giving 12 requests in five cities. The service was explicitly started by the user with
their own Gemini and Tavily credentials. No keys were read into, written to, or included in these
evaluation artifacts.

## Results

| Measure | Count |
| --- | ---: |
| Requests returning HTTP 200 and at least one card | 12/12 (100%) |
| Empty requests | 0/12 |
| Requests ending in an HTTP error, busy message or timeout | 0/12 |
| Returned cards | 25 |
| Cards supported by all applicable source checks | 20/25 (80%) |
| Cards contradicting a required check | 2/25 (8%) |
| Cards with insufficient or ambiguous required evidence | 3/25 (12%) |

The request count is not menu quality. A successful request could contain a recovered upstream
failure because internal retry attempts were not instrumented. The 25-card denominator includes
restaurants repeated across separate queries; it is not 25 independent restaurants or users.

The source review was AI-assisted desk research, separate from the app's own checks. It was not
a blinded human review or a usability study. Detailed audit operationalization was agreed during
review after generation; only the query suite and broad audit requirements were frozen before
inference. There is no inter-reviewer agreement statistic.

## Audit rules and findings

Each card was checked for dish identity, current merchant/city evidence, cuisine, and applicable
taste, region or named-dish constraints. A pass requires support for every applicable criterion;
a demonstrated contradiction takes precedence as fail; missing or ambiguous support gives
insufficient evidence.

- City is interpreted as the requested municipality. Alhambra is not Los Angeles city, although
  it may fit the product's Greater Los Angeles/San Gabriel Valley intent. Ani Ramen's cited menu
  is for Jersey City, not New York City. These are the two strict geographic failures.
- Crispy requires dish-specific crisp/crispy/crunchy evidence. Frying alone does not establish
  that texture. Spasso's Fried Calamari and Hojokban's Honey Fried Chicken are real dishes, but
  their reviewed sources did not substantiate the requested texture.
- Fresh-and-light is a preparation-style proxy supported by menu descriptions, not verified
  nutritional content, actual freshness or food safety. CIAORIGATO's milk-bread phrase had an
  ambiguous canonical item mapping and did not support that preference.
- A description-only returned name can still have supported identity when uniquely mapped to
  a real item. Name-format problems, such as menu descriptions or prices in dish_name, are
  recorded separately from content support.
- Ordering-page availability or a platform's closed label does not by itself establish whether
  a physical restaurant has permanently closed. Access failures and corroborating merchant
  sources are disclosed per card.

This rubric and the expanded query mix differ from the November 16 audit. Do not interpret
20/25 versus 17/26 as a controlled model improvement or restore the slides' 75/76/17 figures.

## Timing and model provenance

Across 12 sequential client HTTP calls: mean 9.491 seconds, median 9.507 seconds, range
3.872 to 13.790 seconds. These observations include server/search/model processing and
internal retries if any, but exclude app startup, browser rendering and manual source review.
They do not establish production tail latency, concurrency or cold-start performance.
No token/billing cost study was performed.

The local application commit is 4be1cda19a19f2e4f893ff6ee6b75f945eb358c4. The named remote
97c44fde4a4cc9f03dea77f18dd111f2313e68f8 revision changes only README and TEAM_GUIDE, as
recorded in the accompanying Snap evaluation. The served index HTML matched the local file.
The submitted Gemini default is gemini-3.5-flash-lite. The live process's environment override
and model snapshot were not independently inspected; see model_provenance.json.

## Reproduce

Start the final online service with your own API keys using the hidden launcher prompts.
From the repository root, choose a new output directory:

```bash
python evaluation/run_final_discover.py --run \
  --protocol evaluation/final_discover_protocol_12.json \
  --base-url http://127.0.0.1:7873 \
  --server-commit YOUR_VERIFIED_SERVING_COMMIT \
  --model YOUR_RECORDED_SERVER_MODEL \
  --output /path/to/a/new/discover-run
```

Without --run the runner prints the plan and makes no API calls. It refuses existing output
directories. Source-audit fields start blank; neither the script nor successful requests
automatically verify menu quality. A future rerun can differ because models, searches and
menus change. Preserve all responses instead of retrying only failed cases to improve a rate.

## Evidence

- protocol.json and request_D01.json through request_D12.json: frozen cases and raw responses.
- requests.json: combined raw logs. summary.json is the immutable request-only summary captured
  before source review, so its menu-audit fields remain null by design.
- evaluation_summary.json: final combined request and source-audit metrics with source hashes.
- card_audit.json and card_audit.csv: all 25 reviewed cards, checks, decisions and evidence URLs.
- card_audit_D01_D06.json and card_audit_D07_D12.json: original review parts and source notes.
- timing_summary.json, model_provenance.json and campaign_integrity.json: timing, provenance
  limitations and raw-record integrity verification.
