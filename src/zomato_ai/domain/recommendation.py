"""Recommendation response models assembled by the orchestrator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RecommendationItem(BaseModel):
    """One ranked restaurant recommendation with dataset-owned facts."""

    model_config = ConfigDict(extra="forbid")

    restaurant_id: str
    name: str
    cuisines: list[str]
    rating: float | None
    estimated_cost: int | None
    budget_band: str | None
    city: str | None
    area: str | None
    rank: int = Field(ge=1)
    explanation: str


class RecommendationMetadata(BaseModel):
    """Operational metadata for the recommendation response."""

    model_config = ConfigDict(extra="forbid")

    candidate_count: int
    total_matches: int
    returned_count: int
    max_candidates: int
    top_k: int
    degraded: bool
    mode: Literal["deterministic_fallback", "groq"]
    filters_applied: dict[str, object]


class RecommendationResponse(BaseModel):
    """Final response returned by the recommendation workflow."""

    model_config = ConfigDict(extra="forbid")

    recommendations: list[RecommendationItem]
    metadata: RecommendationMetadata
    message: str | None = None
