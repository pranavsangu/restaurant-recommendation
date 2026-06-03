# Deployment Plan

This project now includes a **Streamlit entrypoint** for deployment and manual demos.

Streamlit can work well for this project as a demo because the app is interaction-focused and does not need a complex multi-page production frontend yet.

---

## Current App Shape

Implemented today:

- Dataset ingestion from Hugging Face
- Local normalized JSONL cache
- In-memory restaurant index
- Deterministic filtering
- Groq-backed ranking and explanations
- LLM output validation and deterministic fallback
- FastAPI endpoints:
  - `GET /health`
  - `POST /v1/recommendations`
- Basic FastAPI-served frontend at `/`
- Streamlit app entrypoint:
  - `streamlit_app.py`

The Streamlit app reuses the existing Python service logic instead of rebuilding recommendation logic inside the UI.

---

## Recommended Streamlit Shape

The Streamlit entrypoint is:

```text
streamlit_app.py
```

The Streamlit app should call:

```python
from zomato_ai.config import load_settings
from zomato_ai.orchestration import RecommendationService
```

It:

1. Load settings from Streamlit secrets/environment.
2. Initialize `RecommendationService`.
3. Render preference inputs.
4. Call `service.recommend(...)`.
5. Display recommendations.

The same core backend logic remains shared:

```text
Streamlit UI
-> RecommendationService
-> Retriever
-> Groq adapter
-> Validator
-> Response model
```

---

## Required Dependency Update

Streamlit is included in `pyproject.toml`:

```toml
"streamlit>=1.40.0"
```

For Streamlit Cloud, deployment dependencies are also listed in:

```text
requirements.txt
```

The app pins the runtime with:

```text
runtime.txt
```

Keep FastAPI dependencies unless we decide to remove the FastAPI path later.

---

## Secrets

For local development, use `.env`:

```bash
LLM_API_KEY=your_groq_key
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=1
DATASET_CACHE_DIR=.cache/zomato
MAX_CANDIDATES=30
TOP_K_OUTPUT=5
LOG_LEVEL=INFO
```

For Streamlit Community Cloud, use the app secrets UI. Store values like:

```toml
LLM_API_KEY = "your_groq_key"
LLM_MODEL = "llama-3.1-8b-instant"
LLM_BASE_URL = "https://api.groq.com/openai/v1"
LLM_TIMEOUT_SECONDS = "20"
LLM_MAX_RETRIES = "1"
DATASET_CACHE_DIR = ".cache/zomato"
MAX_CANDIDATES = "30"
TOP_K_OUTPUT = "5"
LOG_LEVEL = "INFO"
```

Do not commit `.env`, `.streamlit/secrets.toml`, or real API keys.

---

## Dataset Cache Behavior

The app currently writes normalized records to:

```text
.cache/zomato/restaurants.normalized.jsonl
```

For Streamlit deployment, there are two options.

### Option A: Build Cache on First Request

Let the deployed app download the Hugging Face dataset and build the cache on first run.

Pros:

- Simple repository.
- No dataset artifact committed.

Cons:

- First request can be slow.
- Deployment environment needs network access to Hugging Face.
- Cache may be ephemeral depending on host behavior.

### Option B: Prebuild Cache

Prebuild the normalized JSONL file and include it as an app artifact only if size is acceptable.

Pros:

- Faster startup.
- Less dependency on Hugging Face availability.

Cons:

- Larger repository/artifact.
- Must refresh manually when dataset changes.

For now, use **Option A** unless startup time becomes painful.

---

## Streamlit UI Requirements

The Streamlit app should include inputs for:

- location
- budget
- cuisines
- minimum rating
- extras text
- top-k

It should display:

- restaurant name
- cuisines
- rating
- estimated cost
- area/city
- explanation
- metadata:
  - `mode`
  - `degraded`
  - `candidate_count`
  - `total_matches`

If `mode = "groq"` and `degraded = false`, the app used Groq successfully.

If `mode = "deterministic_fallback"`, the app did not use Groq successfully or LLM config was disabled.

---

## Recommended File Layout

Implemented:

```text
streamlit_app.py
requirements.txt
runtime.txt
```

Optional later:

```text
.streamlit/config.toml
```

Do not commit:

```text
.streamlit/secrets.toml
```

---

## Local Streamlit Run

Run locally:

```bash
python -m pip install -e ".[dev]"
streamlit run streamlit_app.py
```

Then open the local Streamlit URL shown in the terminal.

---

## Deployment Checklist

Before deploying:

1. Rebuild the normalized cache locally after the alias fix.
2. Run tests:

```bash
python3 -m pytest
python3 -m ruff check src tests
```

3. Verify `.env` is not committed:

```bash
git status --ignored --short
```

4. Push code to GitHub.
5. Create Streamlit app from the GitHub repository.
6. Set Streamlit main file path:

```text
streamlit_app.py
```

7. Add Groq secrets in Streamlit settings.
8. Run a live query and confirm response metadata:

```json
{
  "mode": "groq",
  "degraded": false
}
```

---

## Known Follow-Ups

- Consider Streamlit caching with `st.cache_resource` for `RecommendationService`.
- Consider `st.cache_data` or existing JSONL cache for normalized records.
- Add a small deployment smoke-test section after first successful Streamlit deploy.
