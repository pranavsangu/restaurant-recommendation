"""Validated user preference input for restaurant retrieval."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BudgetBand = Literal["low", "medium", "high"]


class UserPreferences(BaseModel):
    """Structured filters and soft preference text supplied by a user."""

    model_config = ConfigDict(extra="forbid")

    location: str | None = Field(default=None, min_length=1)
    budget: BudgetBand | None = None
    cuisines: list[str] = Field(default_factory=list)
    min_rating: float | None = Field(default=None, ge=0, le=5)
    extras_text: str | None = Field(default=None, max_length=500)
    top_k: int | None = Field(default=None, ge=1)

    @field_validator("location", "extras_text", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = " ".join(value.strip().split())
        return normalized or None

    @field_validator("cuisines", mode="before")
    @classmethod
    def normalize_cuisines_input(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value

    @field_validator("cuisines")
    @classmethod
    def normalize_cuisines(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = " ".join(str(value).strip().split())
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized


class PreferenceValidationError(ValueError):
    """Raised when preferences are valid in shape but invalid for runtime config."""


def validate_preferences_for_retrieval(
    preferences: UserPreferences,
    *,
    default_top_k: int,
    max_candidates: int,
) -> UserPreferences:
    """Apply runtime limits that depend on settings, not only schema."""

    top_k = preferences.top_k if preferences.top_k is not None else default_top_k
    if top_k > max_candidates:
        raise PreferenceValidationError("top_k must be less than or equal to MAX_CANDIDATES")
    return preferences.model_copy(update={"top_k": top_k})

