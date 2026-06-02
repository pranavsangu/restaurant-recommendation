# Phase-Wise Implementation Plan

This plan converts the requirements in [`problemStatement.md`](problemStatement.md) and the target design in [`architecture.md`](architecture.md) into an executable roadmap for the AI-assisted restaurant discovery application.

The implementation should preserve the core architecture: **ingestion -> normalization -> deterministic retrieval -> bounded LLM ranking -> validated response rendering**.

---

## Phase 0: Project Foundation

### Goal

Create a clean implementation base with shared conventions, configuration, and local developer workflow.

### Scope

- Choose the first delivery shape:
  - CLI-only for fastest validation, or
  - small backend API with optional web UI.
- Create the initial source layout around architecture boundaries:
  - `config`
  - `data_ingestion`
  - `domain`
  - `retrieval`
  - `llm`
  - `orchestration`
  - `presentation` or `api`
- Add dependency management and a reproducible run command.
- Define environment variables:
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - `LLM_BASE_URL`
  - `DATASET_CACHE_DIR`
  - `MAX_CANDIDATES`
  - `TOP_K_OUTPUT`
- Add `.env.example` without secrets.
- Add basic logging and error handling conventions.

### Deliverables

- Runnable empty application shell.
- Configuration loader that reads environment variables.
- Initial test command.
- README or docs note for local setup.

### Acceptance Checks

- Application starts without an LLM key when only health/startup behavior is used.
- Missing required config produces clear errors only when the related feature is called.
- No secrets are committed.

---

## Phase 1: Dataset Ingestion and Normalization

### Goal

Load the Hugging Face dataset and convert raw rows into stable internal restaurant records.

### Scope

- Load `ManikaSaini/zomato-restaurant-recommendation` from Hugging Face.
- Add an optional local cache to avoid repeated downloads.
- Inspect raw columns and map them into a canonical record:
  - `id`
  - `name`
  - `city`
  - `area`
  - `cuisines`
  - `cost_for_two` or `budget_band`
  - `rating`
  - `raw_attributes`
- Normalize data types:
  - ratings as numeric values
  - costs as numeric values or auditable budget bands
  - cuisines as normalized searchable strings or lists
  - blank or malformed fields handled explicitly
- Create stable IDs from dataset IDs when available, otherwise from a deterministic row hash.
- Mark or skip unusable rows that lack critical display fields.

### Deliverables

- Dataset loader.
- Normalizer.
- Canonical restaurant record type/schema.
- Cache read/write path.
- Unit tests for representative raw rows and edge cases.

### Acceptance Checks

- Dataset can be loaded and normalized locally.
- Normalization is deterministic across runs.
- Invalid or incomplete rows do not crash startup.
- Record counts and skipped-row counts are logged.

---

## Phase 2: In-Memory Index and Deterministic Retrieval

### Goal

Implement the non-LLM recommendation base: structured filtering, sorting, and candidate caps.

### Scope

- Build an in-memory index or embedded local store from normalized rows.
- Define the user preference schema:
  - `location`
  - `budget`
  - `cuisines`
  - `min_rating`
  - `extras_text`
  - `top_k`
- Validate preference input before retrieval.
- Implement deterministic filters:
  - location match on city/area
  - budget band or cost threshold
  - cuisine match
  - minimum rating threshold
  - optional text/tag match for extras when dataset fields support it
- Add deterministic pre-LLM sorting:
  - rating descending
  - cost ascending
  - name or ID as final tie-breaker
- Cap candidate count using `MAX_CANDIDATES`.

### Deliverables

- Preference schema and validation.
- Candidate retriever.
- Deterministic fallback ranking.
- Unit tests for filters, sorting, and caps.

### Acceptance Checks

- Hard constraints are always respected before any LLM call.
- Candidate results are stable for the same input.
- Empty result sets return a helpful response rather than calling the LLM.
- Candidate payload is bounded for latency and token control.

---

## Phase 3: Application Orchestrator

### Goal

Connect ingestion, retrieval, and response assembly behind one recommendation workflow.

### Scope

- Implement `Recommend(preferences)` orchestration:
  1. Ensure the dataset/index is loaded.
  2. Validate preferences.
  3. Retrieve filtered candidates.
  4. Return no-match response if needed.
  5. Prepare candidate subset for ranking.
  6. Return deterministic fallback if LLM is disabled.
- Define the recommendation response model:
  - restaurant ID
  - name
  - cuisines
  - rating
  - estimated cost
  - rank
  - explanation
  - metadata such as candidate count and degradation state
- Ensure display facts are always merged from normalized rows, not generated text.

### Deliverables

- Recommendation orchestrator.
- Response schema/model.
- Deterministic non-LLM response path.
- Integration tests using a small fixture dataset.

### Acceptance Checks

- End-to-end recommendation flow works without an LLM.
- Response fields match canonical dataset facts.
- `top_k` limits the number of returned recommendations.
- Metadata includes candidate count and whether fallback mode was used.

---

## Phase 4: LLM Prompting and Adapter

### Goal

Use an LLM only for bounded ranking and explanations over already-filtered candidates.

### Scope

- Implement an LLM adapter with:
  - Groq base URL/model configuration
  - API key from environment only
  - timeout handling
  - bounded retries
  - structured logging without leaking secrets
- Use Groq as the configured LLM provider:
  - `LLM_BASE_URL=https://api.groq.com/openai/v1`
  - `LLM_MODEL` set to the selected Groq model
  - `LLM_API_KEY` set to the local Groq API key
- Build prompts/messages that include:
  - user preferences
  - capped candidate list
  - strict instruction to choose only supplied IDs
  - instruction to ground explanations in supplied attributes
- Prefer structured output/JSON schema:

```json
{
  "recommendations": [
    {
      "restaurant_id": "candidate-id",
      "rank": 1,
      "explanation": "grounded reason"
    }
  ],
  "optional_summary": "short summary"
}
```

- Keep the candidate payload minimal:
  - ID
  - name
  - cuisines
  - rating
  - cost/budget
  - city/area
  - selected raw attributes useful for explanation

### Deliverables

- Prompt builder.
- Groq-compatible LLM adapter.
- Mock LLM client for tests.
- Golden prompt snapshots or equivalent approval tests.

### Acceptance Checks

- LLM is never called with uncapped candidate sets.
- Prompt contains enough real fields to explain rankings.
- LLM failures degrade to deterministic fallback recommendations.
- API keys are never printed or committed.

---

## Phase 5: LLM Output Validation and Grounding

### Goal

Prevent hallucinated restaurants or fabricated facts from reaching the final response.

### Scope

- Parse LLM output into a strict recommendation schema.
- Validate that every returned `restaurant_id` exists in the request candidate set.
- Drop duplicate, unknown, or malformed recommendations.
- Optionally retry once with a corrective prompt when the model output is invalid.
- Merge final display fields from canonical records:
  - name
  - rating
  - cuisine
  - cost
  - location
- Keep only the explanation text from the model after validation.
- Use deterministic fallback when valid LLM output is insufficient.

### Deliverables

- LLM response parser.
- Candidate allow-list validator.
- Fact merge function.
- Tests for hallucinated IDs, duplicates, malformed JSON, and partial responses.

### Acceptance Checks

- Unknown restaurants never appear in the final output.
- Numeric facts in final output match dataset records.
- Invalid LLM output has a bounded recovery path.
- The user receives useful results even if validation fails.

---

## Phase 6: API or CLI Presentation Layer

### Goal

Expose the recommendation workflow to users in a simple, usable interface.

### Scope

Implement one or both presentation paths.

### API Path

- Add health endpoint:
  - `GET /health`
- Add recommendation endpoint:
  - `POST /v1/recommendations`
- Validate request JSON.
- Map errors to clear status codes.
- Return ranked recommendations and metadata.

### CLI Path

- Add a command that accepts preferences through flags or an input JSON file.
- Print a compact ranked list:
  - name
  - cuisine
  - rating
  - estimated cost
  - explanation
- Include an option for JSON output for testing/demo automation.

### Deliverables

- API controller or CLI command.
- Request/response examples.
- Basic smoke tests.

### Acceptance Checks

- Users can submit location, budget, cuisine, minimum rating, extras, and top-k.
- The output is short, scannable, and grounded.
- Invalid input returns a useful validation message.
- Health check confirms whether the dataset/index is loaded.

---

## Phase 7: Quality, Observability, and Evaluation

### Goal

Make the system testable, debuggable, and trustworthy enough for a demo or portfolio project.

### Scope

- Add structured logs for:
  - request ID
  - candidate count
  - retrieval latency
  - LLM latency
  - fallback/degraded state
- Add tests:
  - normalizer edge cases
  - retrieval predicates
  - schema validation
  - prompt construction
  - orchestrator with mocked LLM
- Create a small manual evaluation rubric:
  - constraints respected
  - explanation grounded in fields
  - ranking usefulness
  - clarity of final output
- Add sample queries for regression checks.

### Deliverables

- Test suite covering critical logic.
- Manual evaluation examples.
- Logging and debug guide.

### Acceptance Checks

- Core tests pass locally.
- Sample queries produce stable, understandable results.
- Fallback behavior is tested.
- Logs help diagnose no-match, LLM-failure, and validation-failure cases.

---

## Phase 8: Packaging and Deployment

### Goal

Prepare the application for repeatable local demo use and optional deployment.

### Scope

- Add a single local run command.
- Package dataset cache behavior for local and container environments.
- Optionally add a container image.
- Document deployment profiles:
  - local/demo single process
  - container with mounted dataset cache
  - future stateless API with shared read-only dataset artifact
- Pin dataset revision or snapshot hash for reproducibility.

### Deliverables

- Local run instructions.
- Optional container configuration.
- Deployment notes.
- Environment variable reference.

### Acceptance Checks

- A new developer can run the app from the docs.
- Dataset loading behavior is reproducible.
- Required environment variables are clearly documented.
- No credentials are baked into artifacts.

---

## Phase 9: Future Enhancements

These are intentionally outside the MVP unless the core workflow is already stable.

- Web UI with preference form and ranked recommendation cards.
- Saved preferences and user accounts.
- Click feedback or online learning.
- Vector search if review text becomes available.
- Admin endpoint for dataset refresh.
- Multi-region or multi-dataset support.
- More advanced explanation evaluation.

---

## Suggested MVP Build Order

1. Phase 0: Project foundation.
2. Phase 1: Dataset ingestion and normalization.
3. Phase 2: Deterministic retrieval.
4. Phase 3: Orchestrator with deterministic fallback.
5. Phase 6: CLI or API surface.
6. Phase 4: LLM adapter and prompt builder.
7. Phase 5: LLM validation and fact merge.
8. Phase 7: Quality and evaluation.
9. Phase 8: Packaging.

This order keeps the application useful before LLM integration is complete and protects the grounding constraint from the beginning.

---

## MVP Definition of Done

The MVP is complete when:

- The dataset loads and normalizes into canonical restaurant records.
- Users can provide location, budget, cuisine, minimum rating, extras, and top-k.
- Candidate filtering is deterministic and tested.
- The LLM receives only capped, filtered candidates.
- Final recommendations contain only restaurants from the candidate set.
- Restaurant facts in the response come from the dataset, not the LLM.
- LLM failures return deterministic fallback results.
- The app can be run locally using documented commands and environment variables.
