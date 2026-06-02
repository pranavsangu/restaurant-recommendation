# Decisions

This is the living implementation decision log for the Zomato AI recommendation project. Update it whenever a new phase is implemented or a major technical choice changes.

---

## Current Stack

| Area | Decision |
| --- | --- |
| Language | Python |
| API | FastAPI |
| CLI | Typer |
| Validation | Pydantic |
| Dataset source | Hugging Face dataset: `ManikaSaini/zomato-restaurant-recommendation` |
| Runtime storage | In-memory index |
| Local persistence | JSONL normalized cache at `.cache/zomato/restaurants.normalized.jsonl` |
| LLM provider | Groq via OpenAI-compatible API |
| Tests | Pytest |
| Linting | Ruff |

---

## Phase 0: Project Foundation

### Status

Implemented.

### Decisions

- Use a Python `src/` layout.
- Keep modules aligned with architecture boundaries:
  - `config`
  - `data_ingestion`
  - `domain`
  - `retrieval`
  - `llm`
  - `orchestration`
  - `api`
  - `presentation`
- Use `.env` for local secrets and `.env.example` for documented config.
- Keep `LLM_API_KEY` optional until LLM-backed ranking is needed.
- Add dependency-free `.env` loading rather than requiring a dotenv package in app code.
- Add basic logging controlled by `LOG_LEVEL`.

### Implemented Files

- `pyproject.toml`
- `README.md`
- `.env.example`
- `src/zomato_ai/config/settings.py`
- `src/zomato_ai/config/logging.py`
- `src/zomato_ai/api/app.py`
- `src/zomato_ai/presentation/cli.py`
- `tests/test_settings.py`

---

## Phase 1: Dataset Ingestion and Normalization

### Status

Implemented.

### Decisions

- Use Hugging Face `datasets` to load the source dataset.
- Normalize rows into a canonical `RestaurantRecord`.
- Use local JSONL cache instead of a database for MVP.
- Keep the cache path configurable through `DATASET_CACHE_DIR`.
- Generate stable row-hash IDs when the dataset does not provide an ID.
- Skip rows only when they cannot be safely displayed, such as missing restaurant name.
- Preserve raw source attributes for future LLM context, while final display facts come from canonical fields.

### Implemented Files

- `src/zomato_ai/domain/restaurant.py`
- `src/zomato_ai/data_ingestion/normalizer.py`
- `src/zomato_ai/data_ingestion/cache.py`
- `src/zomato_ai/data_ingestion/loader.py`
- `tests/test_normalizer.py`
- `tests/test_cache.py`

### Verification

- Unit tests passed.
- Real ingestion completed:
  - total rows: `51717`
  - normalized rows: `51717`
  - skipped rows: `0`

---

## Phase 2: In-Memory Index and Deterministic Retrieval

### Status

Implemented.

### Decisions

- Use an in-memory `RestaurantIndex` for MVP.
- Validate user preferences with Pydantic.
- Apply hard filters before any LLM call:
  - location
  - budget
  - cuisines
  - minimum rating
- Exclude unknown rating/cost only when the corresponding hard filter is set.
- Sort deterministically by:
  1. rating descending
  2. cost ascending
  3. name
  4. ID
- Cap candidate lists with `MAX_CANDIDATES`.
- Keep extras text as a soft preference for the LLM phase.

### Implemented Files

- `src/zomato_ai/domain/preferences.py`
- `src/zomato_ai/retrieval/index.py`
- `src/zomato_ai/retrieval/retriever.py`
- `tests/test_preferences.py`
- `tests/test_retriever.py`

### Verification

- Unit tests passed.
- Ruff checks passed.

---

## Phase 3: Application Orchestrator

### Status

Implemented.

### Decisions

- Add `RecommendationService` as the orchestration boundary.
- Load and build the restaurant index lazily, then reuse it.
- Return deterministic fallback recommendations when LLM ranking is disabled.
- Keep final response facts sourced from `RestaurantRecord`.
- Generate fallback explanations in code.
- Include metadata for candidate counts, total matches, returned count, filters, top-k, and degraded mode.

### Implemented Files

- `src/zomato_ai/domain/recommendation.py`
- `src/zomato_ai/orchestration/recommendation_service.py`
- `tests/test_recommendation_service.py`

### Verification

- Unit and integration tests passed.
- Ruff checks passed.

---

## Phase 4: Groq LLM Prompting and Adapter

### Status

Implemented.

### Decisions

- Use Groq as the LLM provider.
- Use Groq through its OpenAI-compatible chat completions API.
- Read provider config from environment:
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - `LLM_BASE_URL`
  - `LLM_TIMEOUT_SECONDS`
  - `LLM_MAX_RETRIES`
- Keep API keys out of logs and tests.
- Build prompts from only:
  - validated preferences
  - capped candidates
  - minimal candidate fields
- Prompt the model to return strict JSON and choose only supplied candidate IDs.
- Keep LLM tests mocked so unit tests do not use network or API credits.

### Implemented Files

- `src/zomato_ai/llm/prompt_builder.py`
- `src/zomato_ai/llm/adapter.py`
- `tests/test_llm_prompt_builder.py`

### Verification

- Prompt-builder tests passed.
- Full test suite passed.
- Ruff checks passed.

---

## Phase 5: LLM Output Validation and Grounding

### Status

Implemented as part of the Groq integration work.

### Decisions

- Parse LLM output into strict Pydantic models.
- Accept only restaurant IDs present in the candidate set.
- Drop unknown IDs and duplicate IDs.
- Reject malformed JSON.
- Use canonical restaurant records to merge final facts.
- Keep only explanation text from the model.
- Fall back to deterministic recommendations when LLM output is invalid.

### Implemented Files

- `src/zomato_ai/llm/output_validator.py`
- LLM path updates in `src/zomato_ai/orchestration/recommendation_service.py`
- `tests/test_llm_output_validator.py`
- additional LLM-path tests in `tests/test_recommendation_service.py`

### Verification

- LLM validation tests passed.
- Service fallback tests passed.
- Full test suite passed.
- Ruff checks passed.

---

## Manual Testing UI

### Status

Implemented as a basic local frontend.

### Decisions

- Add a simple same-origin HTML page served by FastAPI at `/`.
- Add recommendation API endpoint at `POST /v1/recommendations`.
- Keep the UI lightweight and dependency-free for manual testing.
- Show whether results came from Groq or deterministic fallback through response metadata.

### Implemented Files

- `src/zomato_ai/api/app.py`
- `tests/test_api_app.py`

### Manual Run

```bash
uvicorn zomato_ai.api.app:create_app --factory --reload
```

Open:

```text
http://127.0.0.1:8000/
```

---

## Current Verification Snapshot

Latest known successful checks:

```text
python3 -m pytest
41 passed
```

```text
python3 -m ruff check src tests
All checks passed!
```

---

## Update Rule

When implementing the next phase, update this file with:

1. Phase status.
2. Major technical decisions.
3. Files added or changed.
4. Verification results.
5. Any known limitations or follow-up work.
