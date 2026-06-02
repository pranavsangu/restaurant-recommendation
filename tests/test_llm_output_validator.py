import pytest

from zomato_ai.domain import RestaurantRecord
from zomato_ai.llm import LLMValidationError, parse_and_validate_llm_output


def candidate(candidate_id: str) -> RestaurantRecord:
    return RestaurantRecord(
        id=candidate_id,
        name="Name",
        city=None,
        area=None,
        cuisines=[],
        cost_for_two=None,
        budget_band=None,
        rating=None,
    )


def test_parse_and_validate_llm_output_keeps_only_allowed_unique_ids() -> None:
    output = """
    {
      "recommendations": [
        {"restaurant_id": "r2", "rank": 1, "explanation": "Grounded."},
        {"restaurant_id": "unknown", "rank": 2, "explanation": "Nope."},
        {"restaurant_id": "r2", "rank": 3, "explanation": "Duplicate."},
        {"restaurant_id": "r1", "rank": 4, "explanation": "Also grounded."}
      ]
    }
    """

    parsed = parse_and_validate_llm_output(output, [candidate("r1"), candidate("r2")])

    assert [item.restaurant_id for item in parsed] == ["r2", "r1"]


def test_parse_and_validate_llm_output_rejects_malformed_json() -> None:
    with pytest.raises(LLMValidationError):
        parse_and_validate_llm_output("not json", [candidate("r1")])


def test_parse_and_validate_llm_output_rejects_all_unknown_ids() -> None:
    output = '{"recommendations":[{"restaurant_id":"missing","rank":1,"explanation":"Bad."}]}'

    with pytest.raises(LLMValidationError):
        parse_and_validate_llm_output(output, [candidate("r1")])

