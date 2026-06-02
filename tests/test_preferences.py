import pytest
from pydantic import ValidationError

from zomato_ai.domain import (
    PreferenceValidationError,
    UserPreferences,
    validate_preferences_for_retrieval,
)


def test_user_preferences_normalize_text_and_cuisines() -> None:
    preferences = UserPreferences(
        location="  Bangalore  ",
        cuisines=[" Italian ", "italian", "", "Cafe"],
        extras_text="  quiet   dinner ",
    )

    assert preferences.location == "Bangalore"
    assert preferences.cuisines == ["Italian", "Cafe"]
    assert preferences.extras_text == "quiet dinner"


def test_user_preferences_reject_invalid_rating_and_budget() -> None:
    with pytest.raises(ValidationError):
        UserPreferences(budget="expensive", min_rating=7)


def test_validate_preferences_applies_default_top_k() -> None:
    preferences = validate_preferences_for_retrieval(
        UserPreferences(),
        default_top_k=5,
        max_candidates=30,
    )

    assert preferences.top_k == 5


def test_validate_preferences_rejects_top_k_above_candidate_limit() -> None:
    with pytest.raises(PreferenceValidationError, match="top_k"):
        validate_preferences_for_retrieval(
            UserPreferences(top_k=31),
            default_top_k=5,
            max_candidates=30,
        )

