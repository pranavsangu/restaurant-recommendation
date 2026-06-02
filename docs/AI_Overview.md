# AI Overview

This project uses AI for **ranking and explanation**, not for factual discovery.

The core rule is:

> Code owns restaurant facts and hard filters. The LLM only ranks already-filtered candidates and writes grounded explanations.

---

## What AI Does

The LLM is used after deterministic retrieval has already produced a bounded candidate list.

AI responsibilities:

- Rank candidate restaurants.
- Explain why each restaurant fits the user preferences.
- Optionally help compare tradeoffs between candidates.

AI does **not**:

- Search the full dataset.
- Invent restaurants.
- Decide hard filters.
- Generate ratings, costs, cuisines, or locations.
- Override dataset facts.

---

## Provider

We selected **Groq** as the LLM provider.

The app uses Groq through its OpenAI-compatible chat completions API.

Environment configuration:

```bash
LLM_API_KEY=
LLM_MODEL=llama-3.1-8b-instant
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=20
LLM_MAX_RETRIES=1
```

The API key is read from `.env` and must not be committed.

---

## AI Flow

Current recommendation flow:

```text
User preferences
-> deterministic validation
-> deterministic dataset filters
-> capped candidate list
-> Groq prompt
-> JSON response from LLM
-> output validation
-> merge canonical dataset facts
-> final recommendations
```

If the LLM fails, times out, returns invalid JSON, or returns unknown restaurant IDs, the app falls back to deterministic ranking.

---

## Prompt Builder

Prompt code lives in:

```text
src/zomato_ai/llm/prompt_builder.py
```

The prompt includes:

- validated user preferences
- `top_k`
- capped candidate restaurants
- only minimal candidate fields:
  - ID
  - name
  - cuisines
  - rating
  - cost
  - budget band
  - city/area
  - selected useful attributes

The system prompt tells the model:

- choose only from supplied candidates
- do not invent restaurants
- do not invent facts
- return strict JSON
- ground explanations in supplied attributes

---

## Groq Adapter

Groq adapter code lives in:

```text
src/zomato_ai/llm/adapter.py
```

The adapter:

- reads model/base URL/key from settings
- sends chat completion requests to Groq
- requests JSON output
- applies timeout and bounded retry behavior
- avoids logging secrets

Unit tests use a fake LLM client, so tests do not call Groq or spend API credits.

---

## Output Validation

Validation code lives in:

```text
src/zomato_ai/llm/output_validator.py
```

The validator:

- parses LLM JSON
- validates schema with Pydantic
- accepts only restaurant IDs from the candidate set
- drops duplicate IDs
- rejects malformed output
- rejects responses where no valid candidate IDs remain

Final restaurant facts are merged from `RestaurantRecord`, not trusted from the model.

---

## Orchestration

The LLM path is wired in:

```text
src/zomato_ai/orchestration/recommendation_service.py
```

The service:

1. validates preferences
2. builds or reuses the in-memory restaurant index
3. retrieves deterministic candidates
4. calls Groq when LLM config is enabled
5. validates model output
6. fills missing results with deterministic fallback if needed
7. returns metadata showing whether response mode was `groq` or `deterministic_fallback`

---

## Current Limitations

- We have not created an autonomous agent. The workflow is code-controlled.
- The LLM does not call tools or query the dataset directly.
- Live Groq behavior should be manually smoke-tested with a real API key.
- The current dataset normalization needs a known fix for actual cost/city columns before budget filtering is reliable.

---

## Why This Design

This design keeps the app grounded and testable:

- deterministic filters protect correctness
- candidate caps control cost and latency
- prompt rules constrain the model
- output validation blocks hallucinated restaurants
- canonical records protect factual fields
- deterministic fallback preserves usability when the LLM fails
