# Evaluation Criteria

This document defines how each implementation phase should be evaluated. It is based on [`problemStatement.md`](problemStatement.md), [`architecture.md`](architecture.md), [`Implementation.md`](Implementation.md), and [`edgecases.md`](edgecases.md).

The project-wide quality bar is:

- **Relevance**: user constraints are respected.
- **Grounding**: restaurant facts come from the dataset, not the LLM.
- **Usefulness**: rankings and explanations help users decide quickly.
- **Clarity**: output is short, scannable, and predictable.
- **Resilience**: known edge cases degrade gracefully.

---

## Phase 0: Project Foundation

### Evaluation Goal

Confirm the project can be installed, configured, started, and tested without needing dataset access or LLM credentials.

### Criteria

| Area | Pass condition |
| --- | --- |
| Project layout | Source folders match architecture boundaries: config, ingestion, domain, retrieval, LLM, orchestration, API/presentation. |
| Dependency setup | A fresh environment can install project dependencies from `pyproject.toml`. |
| Configuration | Environment variables are documented and loaded with defaults where safe. |
| Secret handling | `.env.example` exists and no real credentials are committed. |
| Startup behavior | Health or CLI shell runs without `LLM_API_KEY`. |
| Error clarity | Invalid config values produce actionable errors. |
| Testing | At least one test command exists and config tests cover defaults and invalid values. |

### Evidence

- `python -m pip install -e ".[dev]"`
- `pytest`
- CLI health output or API `/health` output.
- Review of `.env.example` and ignored `.env`.

---

## Phase 1: Dataset Ingestion and Normalization

### Evaluation Goal

Confirm raw Hugging Face rows are converted into deterministic, usable canonical restaurant records.

### Criteria

| Area | Pass condition |
| --- | --- |
| Dataset loading | The configured dataset can be loaded from Hugging Face or from local cache. |
| Cache behavior | Existing cache is reused; corrupt or missing cache is handled clearly. |
| Canonical schema | Records include stable `id`, `name`, location, cuisines, rating, cost/budget, and raw attributes. |
| Type normalization | Ratings, costs, cuisines, and location fields are parsed consistently. |
| Stable IDs | The same source row gets the same ID across runs. |
| Bad rows | Missing critical fields are skipped or marked without crashing ingestion. |
| Observability | Record counts, skipped counts, and schema warnings are logged. |
| Tests | Unit tests cover malformed rating, malformed cost, missing name, duplicate rows, and mixed cuisine formats. |

### Evidence

- Ingestion command or startup log showing total and normalized row counts.
- Cache file generated under `DATASET_CACHE_DIR`.
- Unit test results for normalization edge cases.
- A small sample of normalized records.

---

## Phase 2: In-Memory Index and Deterministic Retrieval

### Evaluation Goal

Confirm structured filters and sorting work without the LLM and always produce bounded candidate sets.

### Criteria

| Area | Pass condition |
| --- | --- |
| Preference validation | Location, budget, cuisines, minimum rating, extras, and top-k are validated. |
| Hard filters | Location, budget, cuisine, and minimum rating constraints are respected. |
| Unknown fields | Unknown rating/cost values are excluded from matching hard filters. |
| Sorting | Results are ordered deterministically by rating, cost, then name or ID. |
| Candidate cap | Returned candidate list never exceeds `MAX_CANDIDATES`. |
| Empty results | No-match responses are returned without calling LLM logic. |
| Repeatability | Same input and dataset produce the same candidate order. |
| Tests | Filter, sort, cap, no-match, and invalid preference tests pass. |

### Evidence

- Unit tests with fixture restaurants.
- Sample retrieval output for common and no-match queries.
- Assertion that the LLM adapter is not invoked during retrieval tests.

---

## Phase 3: Application Orchestrator

### Evaluation Goal

Confirm the end-to-end non-LLM recommendation workflow works and response facts come from canonical records.

### Criteria

| Area | Pass condition |
| --- | --- |
| Flow composition | Orchestrator validates input, retrieves candidates, ranks fallback results, and assembles response. |
| Fallback mode | Deterministic recommendations work when LLM is disabled or unavailable. |
| Fact ownership | Name, cuisine, rating, cost, and location are copied from normalized records. |
| Metadata | Response includes candidate count and degraded/fallback state. |
| Top-k behavior | Response length respects `top_k` and available candidate count. |
| No-match behavior | Empty candidate sets return a clear no-match response. |
| Tests | Integration tests cover happy path, no-match path, and LLM-disabled path. |

### Evidence

- Fixture-backed orchestrator test output.
- API or CLI sample response without LLM credentials.
- Test proving generated/display facts are not invented.

---

## Phase 4: LLM Prompting and Adapter

### Evaluation Goal

Confirm LLM calls are bounded, configurable, secret-safe, and limited to ranking/explanation responsibilities.

### Criteria

| Area | Pass condition |
| --- | --- |
| Adapter boundary | LLM logic is isolated behind one client/adapter interface. |
| Env config | API key, model, and provider settings come from environment variables. |
| Prompt grounding | Prompt instructs the model to select only supplied candidate IDs. |
| Prompt content | Candidate payload includes enough real fields for useful explanations. |
| Token control | Prompt uses capped candidates and minimal fields. |
| Timeout/retry | Adapter handles timeout and transient failure with bounded retries. |
| Secret safety | Logs never include API keys or full sensitive config. |
| Tests | Mock LLM tests and prompt snapshot/golden tests pass. |

### Evidence

- Prompt fixture/snapshot reviewed for grounding language.
- Mock LLM test showing request payload uses only capped candidates.
- Timeout/rate-limit test using mocked client.
- Log review showing secrets are redacted or absent.

---

## Phase 5: LLM Output Validation and Grounding

### Evaluation Goal

Confirm invalid, hallucinated, duplicated, or fact-conflicting LLM output cannot corrupt final recommendations.

### Criteria

| Area | Pass condition |
| --- | --- |
| Structured parsing | LLM output is parsed into a strict schema. |
| Candidate allow-list | Every returned ID must exist in the candidate set. |
| Duplicate handling | Duplicate restaurant IDs are dropped or resolved predictably. |
| Unknown IDs | Unknown IDs are rejected and never rendered. |
| Fact merge | Final display facts overwrite any model-provided facts. |
| Partial output | Too few valid results are filled from deterministic fallback or returned with metadata. |
| Failure recovery | Invalid JSON or invalid IDs trigger bounded retry or fallback. |
| Tests | Tests cover malformed JSON, unknown ID, duplicate ID, partial response, and conflicting facts. |

### Evidence

- Validator unit tests.
- Fixture showing a hallucinated restaurant is rejected.
- Fixture showing model-provided incorrect rating is ignored.
- Response metadata showing fallback/degraded state when validation fails.

---

## Phase 6: API or CLI Presentation Layer

### Evaluation Goal

Confirm users can submit preferences and receive clear, grounded recommendations through the chosen interface.

### Criteria

| Area | Pass condition |
| --- | --- |
| Health surface | Health endpoint or CLI command reports process and dataset readiness. |
| Recommendation input | Interface accepts location, budget, cuisines, minimum rating, extras, and top-k. |
| Validation errors | Invalid JSON, wrong types, and invalid values return clear messages. |
| Output shape | Recommendations include name, cuisine, rating, cost, rank, and explanation. |
| No-match UX | Empty results produce a clear no-match response with applied filters or metadata. |
| JSON support | CLI supports JSON output or API returns documented JSON. |
| Smoke tests | Interface tests cover valid request, invalid request, and no-match request. |

### Evidence

- Example request and response.
- CLI transcript or API test client output.
- Smoke test results.
- OpenAPI docs if using FastAPI.

---

## Phase 7: Quality, Observability, and Evaluation

### Evaluation Goal

Confirm the system can be trusted, debugged, and judged against relevance, grounding, usefulness, and clarity.

### Criteria

| Area | Pass condition |
| --- | --- |
| Logging | Logs include request ID, candidate count, retrieval latency, LLM latency, and fallback state. |
| Privacy | Logs avoid API keys and avoid full free-text preferences unless explicitly configured. |
| Test coverage | Critical paths across normalization, retrieval, orchestration, LLM parsing, and fallback are covered. |
| Manual rubric | Sample queries are scored for constraints, explanation grounding, usefulness, and clarity. |
| Edge cases | MVP priority edge cases from `edgecases.md` are covered by tests or documented manual checks. |
| Regression set | Repeatable sample queries exist for common, no-match, sparse-data, and conflicting-preference scenarios. |

### Evidence

- Test report.
- Manual evaluation table for sample queries.
- Example structured logs.
- Checklist mapping MVP edge cases to tests.

---

## Phase 8: Packaging and Deployment

### Evaluation Goal

Confirm another developer can run the project reliably and deploy it without hidden local assumptions.

### Criteria

| Area | Pass condition |
| --- | --- |
| Local run | Fresh setup instructions work from a clean checkout. |
| Env reference | Required and optional environment variables are documented. |
| Dataset reproducibility | Dataset revision or snapshot is pinned or explicitly documented. |
| Cache portability | Cache path is configurable and works locally or can be disabled. |
| Container readiness | Optional container build runs without embedded secrets. |
| Startup clarity | App reports whether dataset is loading, ready, or failed. |
| Deployment notes | Local, container, and future scaled profiles are documented. |

### Evidence

- Fresh-environment setup run.
- Container build/run output if containerized.
- Health check output after startup.
- Documentation review for env variables and cache behavior.

---

## Phase 9: Future Enhancements

### Evaluation Goal

Confirm enhancements do not weaken the core MVP guarantees.

### Criteria

| Enhancement | Required evaluation |
| --- | --- |
| Web UI | UI keeps recommendations scannable and never displays ungrounded facts. |
| Saved preferences | Stored preferences do not leak secrets or sensitive free text in logs. |
| Click feedback | Feedback changes ranking only through auditable logic. |
| Vector search | Retrieved semantic matches still pass deterministic grounding before display. |
| Dataset refresh | Refreshes preserve schema validation, stable IDs where possible, and cache versioning. |
| Multi-dataset support | Source dataset is tracked per restaurant and facts remain traceable. |

### Evidence

- Enhancement-specific tests.
- Manual review against grounding and relevance rules.
- Updated docs and edge-case coverage.

---

## Cross-Phase Release Gate

Before calling any phase complete, verify:

1. Tests for that phase pass.
2. The feature can be run through documented commands.
3. Invalid input or unavailable dependencies fail clearly.
4. No secrets are committed or logged.
5. Facts shown to the user are traceable to normalized dataset records.
6. LLM behavior, when present, is bounded by candidate caps and output validation.
