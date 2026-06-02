"""FastAPI application factory."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from zomato_ai.config import load_settings
from zomato_ai.config.logging import configure_logging
from zomato_ai.orchestration import RecommendationError, RecommendationService

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Zomato AI Recommendations</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1f2933;
      --muted: #65758b;
      --line: #d8dee8;
      --surface: #ffffff;
      --band: #f4f7fb;
      --accent: #d72638;
      --accent-dark: #a61e2c;
      --ok: #0f766e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #fff 0%, var(--band) 100%);
    }
    main {
      width: min(1120px, calc(100vw - 32px));
      margin: 32px auto;
      display: grid;
      grid-template-columns: minmax(280px, 360px) 1fr;
      gap: 24px;
      align-items: start;
    }
    h1 { margin: 0 0 18px; font-size: 28px; letter-spacing: 0; }
    h2 { margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }
    form, .results {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 16px 40px rgba(31, 41, 51, 0.08);
    }
    label { display: block; margin: 14px 0 6px; font-size: 13px; font-weight: 700; }
    input, select, textarea {
      width: 100%;
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }
    textarea { min-height: 78px; resize: vertical; }
    button {
      width: 100%;
      margin-top: 18px;
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font-weight: 800;
      cursor: pointer;
    }
    button:hover { background: var(--accent-dark); }
    button:disabled { opacity: 0.65; cursor: wait; }
    .status { color: var(--muted); margin-bottom: 14px; min-height: 22px; }
    .item {
      border-top: 1px solid var(--line);
      padding: 16px 0;
    }
    .item:first-of-type { border-top: 0; padding-top: 0; }
    .title-row {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
    }
    .name { font-weight: 850; font-size: 17px; }
    .rank { color: var(--accent); font-weight: 850; }
    .meta {
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
    }
    .why { margin: 10px 0 0; line-height: 1.45; }
    .pill { color: var(--ok); font-weight: 800; }
    @media (max-width: 760px) {
      main { grid-template-columns: 1fr; margin-top: 16px; }
    }
  </style>
</head>
<body>
  <main>
    <form id="prefs">
      <h1>Zomato AI</h1>
      <label for="location">Location</label>
      <input id="location" name="location" value="Banashankari" />

      <label for="budget">Budget</label>
      <select id="budget" name="budget">
        <option value="">Any</option>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>

      <label for="cuisines">Cuisines</label>
      <input id="cuisines" name="cuisines" value="North Indian" />

      <label for="min_rating">Minimum rating</label>
      <input id="min_rating" name="min_rating" type="number" min="0" max="5" step="0.1" value="4" />

      <label for="extras_text">Extras</label>
      <textarea id="extras_text" name="extras_text">family dinner, good ambience</textarea>

      <label for="top_k">Results</label>
      <input id="top_k" name="top_k" type="number" min="1" max="10" value="5" />

      <button id="submit" type="submit">Find Restaurants</button>
    </form>

    <section class="results">
      <h2>Recommendations</h2>
      <div id="status" class="status">Ready</div>
      <div id="results"></div>
    </section>
  </main>
  <script>
    const form = document.querySelector("#prefs");
    const statusEl = document.querySelector("#status");
    const resultsEl = document.querySelector("#results");
    const button = document.querySelector("#submit");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      button.disabled = true;
      statusEl.textContent = "Searching...";
      resultsEl.innerHTML = "";

      const formData = new FormData(form);
      const cuisines = String(formData.get("cuisines") || "")
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const payload = {
        location: valueOrNull(formData.get("location")),
        budget: valueOrNull(formData.get("budget")),
        cuisines,
        min_rating: numberOrNull(formData.get("min_rating")),
        extras_text: valueOrNull(formData.get("extras_text")),
        top_k: numberOrNull(formData.get("top_k")),
      };

      try {
        const response = await fetch("/v1/recommendations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Request failed");
        render(data);
      } catch (error) {
        statusEl.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });

    function render(data) {
      const mode = data.metadata?.mode || "unknown";
      const degraded = data.metadata?.degraded ? "fallback" : "Groq";
      statusEl.innerHTML = `<span class="pill">${degraded}</span> · `
        + `${data.metadata.returned_count} of ${data.metadata.total_matches} matches · ${mode}`;
      if (!data.recommendations.length) {
        resultsEl.textContent = data.message || "No matches";
        return;
      }
      resultsEl.innerHTML = data.recommendations.map((item) => `
        <article class="item">
          <div class="title-row">
            <div class="name">${escapeHtml(item.name)}</div>
            <div class="rank">#${item.rank}</div>
          </div>
          <div class="meta">
            <span>${escapeHtml((item.cuisines || []).join(", ") || "Cuisine unavailable")}</span>
            <span>${item.rating ?? "Rating unavailable"}</span>
            <span>${item.estimated_cost ? "₹" + item.estimated_cost : "Cost unavailable"}</span>
            <span>${escapeHtml([item.area, item.city].filter(Boolean).join(", "))}</span>
          </div>
          <p class="why">${escapeHtml(item.explanation)}</p>
        </article>
      `).join("");
    }

    function valueOrNull(value) {
      const text = String(value || "").trim();
      return text ? text : null;
    }
    function numberOrNull(value) {
      const text = String(value || "").trim();
      return text ? Number(text) : null;
    }
    function escapeHtml(value) {
      return String(value || "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
      }[char]));
    }
  </script>
</body>
</html>
"""


def create_app() -> FastAPI:
    """Create the API application.

    The app intentionally exposes only health behavior in Phase 0. Later phases
    will attach recommendation routes after ingestion and retrieval exist.
    """

    settings = load_settings()
    configure_logging(settings)
    app = FastAPI(title="Zomato AI Recommendations", version="0.1.0")
    app.state.settings = settings
    app.state.recommendation_service = RecommendationService(settings=settings)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "dataset_loaded": app.state.recommendation_service._index is not None,
            "llm_enabled": settings.llm_enabled,
            "max_candidates": settings.max_candidates,
            "top_k_output": settings.top_k_output,
        }

    @app.post("/v1/recommendations")
    def recommend(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = app.state.recommendation_service.recommend(payload)
        except RecommendationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return response.model_dump()

    return app
