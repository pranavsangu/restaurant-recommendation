"""Recommendation orchestration for deterministic Phase 3 responses."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from zomato_ai.config import AppSettings
from zomato_ai.data_ingestion import load_restaurant_records
from zomato_ai.domain import (
    PreferenceValidationError,
    RecommendationItem,
    RecommendationMetadata,
    RecommendationResponse,
    RestaurantRecord,
    UserPreferences,
    validate_preferences_for_retrieval,
)
from zomato_ai.llm import (
    GroqLLMClient,
    LLMClient,
    LLMError,
    LLMValidationError,
    build_recommendation_messages,
    parse_and_validate_llm_output,
)
from zomato_ai.retrieval import CandidateRetriever, RestaurantIndex, deterministic_rank

LOGGER = logging.getLogger(__name__)


class RecommendationError(ValueError):
    """Raised when a recommendation request cannot be processed."""


RecordLoader = Callable[[AppSettings], list[RestaurantRecord]]


@dataclass
class RecommendationService:
    """Compose data loading, retrieval, and deterministic response assembly."""

    settings: AppSettings
    record_loader: RecordLoader = load_restaurant_records
    llm_client: LLMClient | None = None
    _index: RestaurantIndex | None = None

    def recommend(
        self,
        preferences_input: UserPreferences | Mapping[str, object],
    ) -> RecommendationResponse:
        preferences = self._validate_preferences(preferences_input)
        index = self._ensure_index()
        retriever = CandidateRetriever(index, max_candidates=self.settings.max_candidates)
        retrieval = retriever.retrieve(preferences)

        if retrieval.is_empty:
            return RecommendationResponse(
                recommendations=[],
                metadata=RecommendationMetadata(
                    candidate_count=0,
                    total_matches=0,
                    returned_count=0,
                    max_candidates=retrieval.max_candidates,
                    top_k=preferences.top_k or self.settings.top_k_output,
                    degraded=not self.settings.llm_enabled,
                    mode="deterministic_fallback",
                    filters_applied=retrieval.filters_applied,
                ),
                message="No restaurants matched the provided filters.",
            )

        top_k = preferences.top_k or self.settings.top_k_output
        recommendations, mode, degraded = self._rank_candidates(
            candidates=retrieval.candidates,
            preferences=preferences,
            top_k=top_k,
        )

        LOGGER.info(
            "Built recommendations mode=%s candidate_count=%s returned_count=%s",
            mode,
            len(retrieval.candidates),
            len(recommendations),
        )

        return RecommendationResponse(
            recommendations=recommendations,
            metadata=RecommendationMetadata(
                candidate_count=len(retrieval.candidates),
                total_matches=retrieval.total_matches,
                returned_count=len(recommendations),
                max_candidates=retrieval.max_candidates,
                top_k=top_k,
                degraded=degraded,
                mode=mode,
                filters_applied=retrieval.filters_applied,
            ),
            message=None,
        )

    def _validate_preferences(
        self, preferences_input: UserPreferences | Mapping[str, object]
    ) -> UserPreferences:
        try:
            preferences = (
                preferences_input
                if isinstance(preferences_input, UserPreferences)
                else UserPreferences.model_validate(preferences_input)
            )
            return validate_preferences_for_retrieval(
                preferences,
                default_top_k=self.settings.top_k_output,
                max_candidates=self.settings.max_candidates,
            )
        except (ValidationError, PreferenceValidationError) as exc:
            raise RecommendationError(str(exc)) from exc

    def _ensure_index(self) -> RestaurantIndex:
        if self._index is None:
            records = self.record_loader(self.settings)
            self._index = RestaurantIndex.build(records)
            LOGGER.info("Built restaurant index records=%s", len(self._index))
        return self._index

    def _rank_candidates(
        self,
        *,
        candidates: list[RestaurantRecord],
        preferences: UserPreferences,
        top_k: int,
    ) -> tuple[list[RecommendationItem], str, bool]:
        if self.settings.llm_enabled:
            try:
                return self._rank_with_llm(
                    candidates=candidates,
                    preferences=preferences,
                    top_k=top_k,
                )
            except (LLMError, LLMValidationError) as exc:
                LOGGER.warning("LLM ranking failed; using deterministic fallback: %s", exc)

        return (
            _deterministic_recommendations(candidates, preferences=preferences, top_k=top_k),
            "deterministic_fallback",
            True,
        )

    def _rank_with_llm(
        self,
        *,
        candidates: list[RestaurantRecord],
        preferences: UserPreferences,
        top_k: int,
    ) -> tuple[list[RecommendationItem], str, bool]:
        client = self.llm_client or GroqLLMClient(self.settings)
        messages = build_recommendation_messages(preferences, candidates, top_k=top_k)
        raw_output = client.complete(messages)
        llm_recommendations = parse_and_validate_llm_output(raw_output, candidates)

        by_id = {candidate.id: candidate for candidate in candidates}
        selected: list[RecommendationItem] = []
        selected_ids: set[str] = set()
        for llm_recommendation in llm_recommendations[:top_k]:
            record = by_id[llm_recommendation.restaurant_id]
            selected.append(
                _to_recommendation_item(
                    record,
                    rank=len(selected) + 1,
                    preferences=preferences,
                    explanation=llm_recommendation.explanation,
                )
            )
            selected_ids.add(record.id)

        if len(selected) < top_k:
            fallback_items = _deterministic_recommendations(
                [candidate for candidate in candidates if candidate.id not in selected_ids],
                preferences=preferences,
                top_k=top_k - len(selected),
                starting_rank=len(selected) + 1,
            )
            selected.extend(fallback_items)

        return selected, "groq", False


def _to_recommendation_item(
    record: RestaurantRecord,
    *,
    rank: int,
    preferences: UserPreferences,
    explanation: str | None = None,
) -> RecommendationItem:
    return RecommendationItem(
        restaurant_id=record.id,
        name=record.name,
        cuisines=record.cuisines,
        rating=record.rating,
        estimated_cost=record.cost_for_two,
        budget_band=record.budget_band,
        city=record.city,
        area=record.area,
        rank=rank,
        explanation=explanation or _deterministic_explanation(record, preferences),
    )


def _deterministic_recommendations(
    candidates: list[RestaurantRecord],
    *,
    preferences: UserPreferences,
    top_k: int,
    starting_rank: int = 1,
) -> list[RecommendationItem]:
    selected = deterministic_rank(candidates)[:top_k]
    return [
        _to_recommendation_item(record, rank=index + starting_rank, preferences=preferences)
        for index, record in enumerate(selected)
    ]


def _deterministic_explanation(record: RestaurantRecord, preferences: UserPreferences) -> str:
    reasons: list[str] = []

    if record.rating is not None:
        reasons.append(f"rated {record.rating:g}")
    if preferences.cuisines and record.cuisines:
        matched = _matched_cuisines(record.cuisines, preferences.cuisines)
        if matched:
            reasons.append(f"matches {', '.join(matched)} cuisine")
    elif record.cuisines:
        reasons.append(f"serves {', '.join(record.cuisines[:2])}")
    if record.budget_band is not None:
        reasons.append(f"fits the {record.budget_band} budget band")
    if preferences.location and (record.area or record.city):
        reasons.append(f"is in {record.area or record.city}")

    if not reasons:
        return "Matches the provided restaurant filters."

    return "Good deterministic match because it " + ", ".join(reasons) + "."


def _matched_cuisines(record_cuisines: list[str], requested_cuisines: list[str]) -> list[str]:
    requested = {cuisine.lower(): cuisine for cuisine in requested_cuisines}
    return [cuisine for cuisine in record_cuisines if cuisine.lower() in requested]
