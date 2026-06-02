# Problem Statement

**AI-assisted restaurant discovery (Zomato-style)** — structured listings plus an LLM for ranking and explanations.

| Field | Detail |
| --- | --- |
| **Dataset** | [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) (Hugging Face) |
| **Repo status** | Documentation-first; implementation planned |

---

## 1. Project context

This repository will grow into a small **application or service** that combines:

| Piece | Role |
| --- | --- |
| **Structured data** | Real restaurant rows — correct filters and facts |
| **LLM** | Ranking, comparison, and short natural-language rationales |

Together, results should feel **personal and easy to scan**, not like a raw filtered table.

---

## 2. Problem we are solving

| Pain point | Detail |
| --- | --- |
| Soft preferences | Phrases like “quick,” “good for a date,” or “quiet” are hard to encode with filters alone |
| Facts vs. reasons | Location, cuisine, price, and rating are necessary but don’t explain *why* A beats B |
| Too much choice | Users need a **short ranked list** and **trustworthy one-line reasons**, not dozens of rows |

> **Goal.** Narrow the catalog with explicit preferences, then use an LLM to **rank**, **compare**, and **explain** a small set of options so decisions are fast.

---

## 3. Objectives

Build an application that:

| # | Objective |
| --- | --- |
| 1 | **Ingest** the dataset and expose fields for filter + display (name, area/city, cuisines, cost, rating, …) |
| 2 | **Collect** preferences: location, budget tier, cuisines, minimum rating, extras (e.g. family-friendly, fast service) |
| 3 | **Filter** candidates deterministically from structured input (ground truth = dataset, not the model) |
| 4 | **Call an LLM** with prompts that rank candidates and yield explanations **grounded in supplied rows** |
| 5 | **Render** top picks with cuisine, rating, cost, and a short “why this fits” per item |

---

## 4. Intended users

| User | Need |
| --- | --- |
| **Diners** | Options under place / budget / taste constraints |
| **Builders** | A repeatable pattern: filter → LLM reasoning → UI or API (portfolio / demo) |

---

## 5. System workflow

### 5.1 Data ingestion

- Load and preprocess the Hugging Face dataset
- Normalize types (ratings, cost buckets), handle gaps, keep fields needed for filters and for the LLM context

### 5.2 User input

| Preference | Examples / notes |
| --- | --- |
| Location | Delhi, Bangalore, … |
| Budget | Low / medium / high or bands aligned to the dataset |
| Cuisine | Italian, Chinese, … |
| Minimum rating | Threshold on rating field |
| Extras | Family-friendly, quick service, … (map to text/tags if data allows) |

### 5.3 Integration layer

- Produce a **candidate set** after filters (cap size for latency and tokens)
- Pass candidates as **structured input** (JSON or bullets) into the LLM
- Prompt so the model **only picks from that list** and **grounds explanations in real attributes**

### 5.4 Recommendation engine (LLM)

- **Rank** within candidates
- **Explain** fit vs. stated preferences
- Optionally **summarize** tradeoffs (e.g. value vs. top rating)

### 5.5 Output display

For each recommended place, show:

1. Restaurant name
2. Cuisine
3. Rating
4. Estimated cost
5. AI-generated explanation

---

## 6. Scope and constraints

| Area | Rule |
| --- | --- |
| **Grounding** | Final picks must come from **filtered rows** sent to the LLM — no invented venues |
| **Secrets** | LLM keys via **environment config** only; do not commit credentials |
| **Quality bar** | Mix of **relevance** (constraints respected), **usefulness** (copy matches real fields), **clarity** (few strong recommendations) |

---

## 7. Repository status

`docs/problemStatement.md` holds **intent and requirements**. Planned work: ingestion, API or CLI, UI, and LLM wiring — aligned with **Section 5** (system workflow).

---

## 8. Summary

> **Structured filtering** for correctness · **LLM ranking and explanations** for usability · **Clear UI** so users get a short, actionable list.
