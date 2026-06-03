"""Streamlit entrypoint for the Zomato AI recommendation demo."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from zomato_ai.config import ConfigError, load_settings  # noqa: E402
from zomato_ai.config.logging import configure_logging  # noqa: E402
from zomato_ai.orchestration import RecommendationError, RecommendationService  # noqa: E402

st.set_page_config(
    page_title="Zomato AI Recommendations",
    layout="wide",
)


SECRET_KEYS = (
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "LLM_TIMEOUT_SECONDS",
    "LLM_MAX_RETRIES",
    "DATASET_CACHE_DIR",
    "MAX_CANDIDATES",
    "TOP_K_OUTPUT",
    "LOG_LEVEL",
)


def main() -> None:
    _apply_streamlit_secrets_to_environment()

    try:
        settings = load_settings()
    except ConfigError as exc:
        st.error(str(exc))
        return

    configure_logging(settings)
    service = _get_recommendation_service()

    st.title("Zomato AI Recommendations")
    st.caption("Structured filtering first. Groq ranking only after candidates are grounded.")

    with st.sidebar:
        st.header("Preferences")
        location_options = service.known_locations()
        default_location_index = _default_location_index(location_options, "Banashankari")
        location = st.selectbox(
            "Location",
            options=location_options,
            index=default_location_index,
        )
        budget = st.selectbox("Budget", options=["Any", "low", "medium", "high"], index=0)
        cuisines = st.text_input("Cuisines", value="North Indian")
        min_rating = st.slider("Minimum rating", 0.0, 5.0, 4.0, 0.1)
        extras_text = st.text_area("Extras", value="family dinner, good ambience")
        top_k = st.number_input("Results", min_value=1, max_value=10, value=settings.top_k_output)
        submitted = st.button("Find restaurants", type="primary", use_container_width=True)

    _render_status(settings)

    if not submitted:
        st.info("Set preferences in the sidebar and run a recommendation.")
        return

    payload = {
        "location": _clean_optional(location),
        "budget": None if budget == "Any" else budget,
        "cuisines": _split_csv(cuisines),
        "min_rating": min_rating,
        "extras_text": _clean_optional(extras_text),
        "top_k": int(top_k),
    }

    with st.spinner("Finding grounded recommendations..."):
        try:
            response = service.recommend(payload)
        except RecommendationError as exc:
            st.error(str(exc))
            return

    _render_metadata(response.metadata.model_dump())

    if not response.recommendations:
        st.warning(response.message or "No restaurants matched the provided filters.")
        return

    for item in response.recommendations:
        with st.container(border=True):
            left, right = st.columns([4, 1])
            with left:
                st.subheader(f"{item.rank}. {item.name}")
                st.write(item.explanation)
            with right:
                st.metric("Rating", item.rating if item.rating is not None else "N/A")

            facts = [
                ", ".join(item.cuisines) if item.cuisines else "Cuisine unavailable",
                f"Cost for two: Rs. {item.estimated_cost}"
                if item.estimated_cost
                else "Cost unavailable",
                ", ".join(value for value in [item.area, item.city] if value),
                item.budget_band or "Budget unavailable",
            ]
            st.caption(" · ".join(value for value in facts if value))


@st.cache_resource(show_spinner=False)
def _get_recommendation_service() -> RecommendationService:
    settings = load_settings()
    return RecommendationService(settings=settings)


def _apply_streamlit_secrets_to_environment() -> None:
    for key in SECRET_KEYS:
        if key in os.environ:
            continue
        try:
            value = st.secrets.get(key)
        except (FileNotFoundError, KeyError):
            value = None
        if value is not None:
            os.environ[key] = str(value)


def _render_status(settings) -> None:
    mode = "Groq enabled" if settings.llm_enabled else "Deterministic fallback only"
    st.write(f"**Runtime:** {mode}")


def _render_metadata(metadata: dict[str, Any]) -> None:
    cols = st.columns(4)
    cols[0].metric("Mode", str(metadata["mode"]))
    cols[1].metric("Returned", metadata["returned_count"])
    cols[2].metric("Matches", metadata["total_matches"])
    cols[3].metric("Candidates", metadata["candidate_count"])
    if metadata["degraded"]:
        st.warning("Using deterministic fallback.")
    else:
        st.success("Groq ranking succeeded.")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _clean_optional(value: str) -> str | None:
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _default_location_index(options: list[str], default: str) -> int:
    try:
        return options.index(default)
    except ValueError:
        return 0


if __name__ == "__main__":
    main()
