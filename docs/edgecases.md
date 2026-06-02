# Edge Cases

This document lists edge cases to handle while implementing the AI-assisted restaurant discovery application described in [`problemStatement.md`](problemStatement.md), [`architecture.md`](architecture.md), and [`Implementation.md`](Implementation.md).

The main principle is simple: **structured code owns facts and constraints; the LLM only ranks and explains candidates that code has already approved**.

---

## 1. Dataset Ingestion Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Hugging Face dataset is unavailable | Fail startup clearly, or use an existing local cache if present. |
| Dataset schema changes | Log unknown/missing columns and fail normalization if critical fields cannot be mapped. |
| Empty dataset split | Return a startup/index error; do not serve recommendation requests with an empty index unless explicitly configured. |
| Duplicate restaurant rows | Deduplicate by dataset ID if present; otherwise use normalized name + location or row hash. |
| Missing restaurant name | Skip row because it cannot be displayed or safely recommended. |
| Missing location | Keep row only if location is optional for the query path; otherwise exclude from location-filtered results. |
| Missing cuisine | Keep as `unknown` only if display can handle it; do not match it to cuisine filters. |
| Malformed rating | Parse if safe; otherwise set rating to null and exclude from `min_rating` matches. |
| Rating outside expected range | Clamp only if dataset rules justify it; otherwise mark invalid and log. |
| Malformed cost | Set cost/budget to unknown; exclude from hard budget filters. |
| Mixed currency or cost formats | Normalize through a single parser and record unparseable examples for inspection. |
| Blank optional attributes | Keep row, but omit those attributes from LLM context. |

---

## 2. Normalization Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Cuisine string contains many separators | Normalize common separators such as commas, slashes, and pipes. |
| Case and spacing differences | Use lowercase trimmed values for matching; preserve original values for display when useful. |
| Area/city names contain punctuation | Normalize for filtering, preserve canonical display text. |
| Cost cannot map cleanly to budget tier | Use `unknown`; do not guess low/medium/high. |
| Generated stable ID changes between runs | Treat as a bug; IDs must be deterministic for the same source row. |
| Multiple restaurants share the same name | Keep distinct IDs and include location/cost/rating in candidate context. |
| Critical field count is unexpectedly low | Log a warning or fail ingestion based on configured quality threshold. |

---

## 3. User Preference Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Empty request body | Return validation error with required fields or defaults. |
| Unknown location | Return no-match response with suggestions if available. |
| Location typo | Optionally support fuzzy matching later; MVP should avoid guessing silently. |
| Budget omitted | Treat as no budget filter. |
| Cuisine omitted | Treat as no cuisine filter. |
| Minimum rating omitted | Use default or no rating filter, based on product decision. |
| Minimum rating outside range | Return validation error. |
| `top_k` is missing | Use configured default. |
| `top_k` is zero or negative | Return validation error. |
| `top_k` is too large | Clamp to configured maximum or return validation error. |
| Extras text is very long | Truncate or reject according to a defined length limit. |
| Extras text contains prompt injection | Treat it as user preference text only; never let it override system instructions. |

---

## 4. Deterministic Retrieval Edge Cases

| Edge case | Expected handling |
| --- | --- |
| No candidates after hard filters | Return a no-match response; do not call the LLM. |
| Too many candidates after filtering | Sort deterministically and cap using `MAX_CANDIDATES`. |
| Candidate count is less than `top_k` | Return only available candidates. |
| Candidate has unknown rating | Exclude from `min_rating` queries; allow only when no rating filter is applied. |
| Candidate has unknown cost | Exclude from budget-filtered queries; allow only when no budget filter is applied. |
| Tie on rating and cost | Use name or ID as final deterministic tie-breaker. |
| Extras cannot be mapped to data fields | Pass extras to LLM as soft preference only after hard filters are complete. |
| Filters are too restrictive | Return useful metadata showing zero candidates and which filters were applied. |

---

## 5. LLM Prompt Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Candidate list is empty | Do not build or send an LLM prompt. |
| Candidate payload exceeds token budget | Reduce fields, lower `MAX_CANDIDATES`, or use deterministic fallback. |
| Candidate names contain special characters | Serialize candidates as structured JSON, not fragile free text. |
| User extras ask for unavailable facts | Instruct the model to explain only using supplied attributes. |
| User asks for restaurants outside candidate list | Model instruction must require choosing only supplied candidate IDs. |
| Prompt injection appears in restaurant data | Treat dataset text as data, not instructions. |
| Prompt injection appears in user extras | Treat extras as preference content, not instructions. |

---

## 6. LLM Response Edge Cases

| Edge case | Expected handling |
| --- | --- |
| LLM returns invalid JSON | Retry once if configured; otherwise use deterministic fallback. |
| LLM returns restaurant names instead of IDs | Accept only if they can be mapped unambiguously to candidate IDs; otherwise reject. |
| LLM returns unknown restaurant ID | Drop the item and optionally retry once. |
| LLM returns duplicate IDs | Keep the first valid instance and drop duplicates. |
| LLM returns more than `top_k` items | Keep only the first valid `top_k`. |
| LLM returns fewer than `top_k` items | Fill from deterministic fallback candidates or return fewer with metadata. |
| LLM changes rating/cost/cuisine facts | Ignore generated facts and merge canonical facts from normalized records. |
| LLM explanation mentions unsupported facts | Prefer validation/rubric checks; for MVP, keep prompts strict and monitor examples. |
| LLM call times out | Use deterministic fallback and mark response as degraded. |
| LLM API returns rate limit | Retry within bounded policy; otherwise degrade gracefully. |
| LLM API key is missing | Skip LLM path and return deterministic fallback, or fail only if LLM is required by mode. |

---

## 7. Response Rendering Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Recommendation has unknown cuisine | Display `Cuisine unavailable` or omit the field consistently. |
| Recommendation has unknown cost | Display `Cost unavailable` or omit the field consistently. |
| Explanation is empty | Use a short templated explanation from deterministic fields. |
| Explanation is too long | Truncate to the UI/API limit without cutting words awkwardly. |
| Multiple recommendations have same name | Include area/city to disambiguate. |
| No recommendations available | Show a clear no-match state with applied filters. |

---

## 8. API or CLI Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Invalid JSON request | Return a clear parse error. |
| Unknown request fields | Ignore or reject based on schema strictness; document the behavior. |
| Wrong data type for field | Return validation error with field name. |
| Health check before dataset load completes | Return loading/unhealthy status with reason. |
| Concurrent requests during startup | Queue, reject with loading status, or block until index is ready. |
| CLI input file missing | Print a clear file-not-found error. |
| CLI output is piped | Support JSON output mode for automation. |

---

## 9. Cache and Deployment Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Cache directory is missing | Create it if allowed; otherwise continue without cache or fail clearly. |
| Cache file is corrupt | Ignore cache, reload dataset, and replace cache if possible. |
| Cache schema version is old | Rebuild cache from source dataset. |
| Dataset revision changes | Pin revision for reproducibility; rebuild intentionally when updated. |
| Container has read-only filesystem | Use configurable cache path or disable cache. |
| Multiple app instances build cache simultaneously | Use simple locking or prebuilt dataset artifacts in scaled deployments. |

---

## 10. Observability and Testing Edge Cases

| Edge case | Expected handling |
| --- | --- |
| Logs include sensitive values | Redact API keys and avoid logging full free-text preferences by default. |
| Test fixtures drift from real schema | Include a schema inspection test or fixture refresh process. |
| Mock LLM is too permissive | Add tests for invalid JSON, hallucinated IDs, duplicates, and partial responses. |
| Fallback path is untested | Include explicit tests where LLM fails or is disabled. |
| Evaluation only checks happy path | Add sample queries for no-match, sparse data, and conflicting preferences. |

---

## Priority Edge Cases for MVP

Handle these before considering the MVP complete:

1. Missing or malformed dataset fields.
2. No candidates after filters.
3. Too many candidates before the LLM call.
4. Missing LLM key or LLM timeout.
5. Invalid LLM JSON.
6. Unknown or duplicate restaurant IDs from the LLM.
7. Generated facts conflicting with dataset facts.
8. Oversized `top_k` or invalid user preferences.
9. Corrupt or missing dataset cache.
10. Prompt injection in user extras or dataset text.
