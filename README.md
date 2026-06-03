# Zomato AI Recommendations

AI-assisted restaurant discovery using structured filtering plus grounded LLM ranking and explanations.

The current implementation is Phase 0: project foundation, configuration, package layout, and runnable app shells.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Environment

Copy `.env.example` to `.env` for local development. Do not commit real credentials.

```bash
cp .env.example .env
```

## Run

CLI health check:

```bash
zomato-ai health
```

Build the normalized dataset cache:

```bash
zomato-ai ingest
```

API server:

```bash
uvicorn zomato_ai.api.app:create_app --factory --reload
```

Then open:

```text
http://127.0.0.1:8000/
GET http://127.0.0.1:8000/health
POST http://127.0.0.1:8000/v1/recommendations
```

Streamlit demo:

```bash
streamlit run streamlit_app.py
```

## Test

```bash
pytest
```
