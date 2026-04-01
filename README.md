# Fashion Inspiration Library

This repo is a lightweight implementation for the "Fashion Garment Classification & Inspiration Web App" brief. It demonstrates a simple web app where users can upload photos of garments, have them classified by an LLM into structured metadata and natural language descriptions, and then search and filter across their collection with both AI-generated and user-provided annotations. 

- `app/prompts` for model instructions
- `app/llm_clients` for provider wrappers
- `app/guardrails` for validation and normalization
- `app/token_calculation` for prompt cost estimates
- `app/data_models` for request, response, and full-text search models
- `app/utils` for config, parsing, and file helpers
- `app/agent_tracing` for request traces
- `app/api` and `app/api/routers` for the web layer
- `app/services` and `app/repositories` for workflow and persistence


## Features

- Upload garment photos from the browser
- Classify each photo into a natural-language description plus structured metadata
- Store results in SQLite
- Search with hybrid query handling: an LLM interprets natural-language queries into filters, then SQLite FTS5 searches descriptions, trend notes, and user annotations
- Filter on garment, color, style, material, occasion, designer, location, and time
- Add designer notes and tags that stay distinct from AI-generated metadata
- Record simple request traces and token estimates for each classification run
- In OpenAI mode, store real `input_tokens`, `output_tokens`, `total_tokens`, and calculated USD cost from the API response usage object

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m app.main
```

Open the app on the host and port from `.env`. With the current default config, that is `http://127.0.0.1:8000`.

If `8000` is busy, override it from the command line:

```bash
python -m app.main --port 8005
```

The app loads `.env` automatically. By default, `.env.example` is already configured for `MODEL_PROVIDER=openai`.

Optional pricing overrides for cost calculation:

```bash
OPENAI_INPUT_COST_PER_MILLION=
OPENAI_CACHED_INPUT_COST_PER_MILLION=
OPENAI_OUTPUT_COST_PER_MILLION=
```

If these are left blank, the app uses built-in pricing defaults for known models such as `gpt-4o-mini`.

## Project Layout

```text
/app
  /api
  /agent_tracing
  /data_models
  /guardrails
  /llm_clients
  /prompts
  /repositories
  /services
  /token_calculation
  /utils
/eval
/tests
README.md
```

## Tests

Run:

```bash
pytest
```

Included coverage:

- Unit test for model-output JSON parsing
- Integration test for location and time filters
- End-to-end test for upload, classify, annotate, and filter

## Evaluation

The supplied Pexels fashion page is used as the seed source for the evaluation set.

- `eval/build_pexels_seed_set.py` scrapes image URLs from `https://www.pexels.com/search/fashion/`
- `eval/download_pexels_images.py` downloads a local sample-image folder from that same page
- `eval/pexels_test_set.json` is the generated starter dataset
- `eval/sample_images/` contains the downloaded local image samples plus `manifest.json`
- `eval/evaluate_classifier.py` downloads those images and reports per-attribute accuracy
- The generated seed set currently contains 54 images from the Pexels page captured on April 1, 2026
- On first startup with an empty database, the app imports the downloaded local samples into the library automatically when `SEED_SAMPLE_DATA=true`

Build the dataset:

```bash
python eval/build_pexels_seed_set.py
```

Download the local sample image folder:

```bash
python eval/download_pexels_images.py
```

Run the evaluator with the mock client:

```bash
python eval/evaluate_classifier.py --provider mock
```

Quick smoke run:

```bash
python eval/evaluate_classifier.py --provider mock --limit 5
```

Run the evaluator with OpenAI:

```bash
python eval/evaluate_classifier.py --provider openai --model gpt-4o-mini --api-key "$OPENAI_API_KEY"
```

### Important note about labels

The checked-in Pexels dataset is a **heuristic seed set**, not a gold-standard manually reviewed benchmark. The evaluator only scores fields that have a seed label and reports coverage per attribute. In the current generated set, label coverage is strongest for `garment_type`, `style`, and `occasion`, weaker for `material`, and effectively absent for `country`. For a final submission, I would manually review all 50-100 images and tighten the expected labels before trusting the accuracy numbers.

## Architecture Notes

- FastAPI keeps the API small and easy to run locally.
- SQLite keeps setup minimal and gives full-text search through FTS5.
- The default mock client makes the app demoable without external dependencies.
- The OpenAI client is isolated behind `app/llm_clients` so the provider can be swapped later.
- Search is hybrid: the LLM interprets the query into structured filters, while SQLite still does the actual text retrieval.
- Dynamic filters are generated from stored data, not hardcoded.

## Tradeoffs

- The UI is intentionally thin. It is enough to prove the workflow, not a production design system.
- Token counting is an estimate, not a billing-grade calculation.
- For OpenAI responses, token counts come from the API `usage` object. The fallback estimate is only used for mock/seed data or missing usage metadata.
- The OpenAI response parsing is intentionally small and assumes text-based JSON output.
- The evaluation dataset is present and runnable, but the labels still need full manual review for a real benchmark.
