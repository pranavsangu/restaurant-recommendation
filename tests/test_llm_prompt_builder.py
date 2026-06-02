import json

from zomato_ai.domain import RestaurantRecord, UserPreferences
from zomato_ai.llm import build_recommendation_messages


def test_prompt_builder_includes_grounding_rules_and_minimal_candidates() -> None:
    candidate = RestaurantRecord(
        id="r1",
        name="Jalsa",
        city="Bangalore",
        area="Banashankari",
        cuisines=["North Indian"],
        cost_for_two=800,
        budget_band="medium",
        rating=4.1,
        raw_attributes={"dish_liked": "Pasta", "phone": "secret-ish"},
    )

    messages = build_recommendation_messages(
        UserPreferences(location="Banashankari", cuisines=["North Indian"], top_k=1),
        [candidate],
        top_k=1,
    )

    assert messages[0]["role"] == "system"
    assert "Do not invent restaurants" in messages[0]["content"]
    payload = json.loads(messages[1]["content"])
    assert payload["top_k"] == 1
    assert payload["candidates"][0]["id"] == "r1"
    assert payload["candidates"][0]["attributes"] == {"dish_liked": "Pasta"}

