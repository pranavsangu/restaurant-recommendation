"""Parse and validate grounded LLM ranking output."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from zomato_ai.domain import RestaurantRecord


class LLMValidationError(ValueError):
    """Raised when LLM output cannot produce valid grounded recommendations."""


class LLMRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    restaurant_id: str
    rank: int = Field(ge=1)
    explanation: str = Field(min_length=1)


class LLMRecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recommendations: list[LLMRecommendation]
    optional_summary: str | None = None


def parse_and_validate_llm_output(
    raw_output: str,
    candidates: list[RestaurantRecord],
) -> list[LLMRecommendation]:
    """Return valid, deduped recommendations whose IDs are in the candidate set."""

    candidate_ids = {candidate.id for candidate in candidates}
    try:
        parsed_json = json.loads(raw_output)
        parsed = LLMRecommendationResponse.model_validate(parsed_json)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMValidationError("LLM output was not valid recommendation JSON") from exc

    valid: list[LLMRecommendation] = []
    seen: set[str] = set()
    for recommendation in sorted(parsed.recommendations, key=lambda item: item.rank):
        if recommendation.restaurant_id not in candidate_ids:
            continue
        if recommendation.restaurant_id in seen:
            continue
        seen.add(recommendation.restaurant_id)
        valid.append(recommendation)

    if not valid:
        raise LLMValidationError("LLM output did not contain any valid candidate IDs")

    return valid

