"""Prompt construction for grounded Groq ranking requests."""

from __future__ import annotations

import json
from typing import Any

from zomato_ai.domain import RestaurantRecord, UserPreferences


def build_recommendation_messages(
    preferences: UserPreferences,
    candidates: list[RestaurantRecord],
    *,
    top_k: int,
) -> list[dict[str, str]]:
    """Build strict messages for ranking already-filtered candidates."""

    candidate_payload = [_candidate_payload(candidate) for candidate in candidates]
    user_payload = {
        "preferences": preferences.model_dump(),
        "top_k": top_k,
        "candidates": candidate_payload,
    }

    return [
        {
            "role": "system",
            "content": (
                "You rank restaurants for a Zomato-style recommendation app. "
                "Use only the candidate restaurants supplied by the user message. "
                "Do not invent restaurants, IDs, ratings, prices, cuisines, locations, or facts. "
                "Return only valid JSON with this shape: "
                '{"recommendations":[{"restaurant_id":"candidate-id","rank":1,'
                '"explanation":"one grounded sentence"}],"optional_summary":"short string"}. '
                "Explanations must reference only supplied candidate attributes."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=True, sort_keys=True),
        },
    ]


def _candidate_payload(candidate: RestaurantRecord) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "name": candidate.name,
        "cuisines": candidate.cuisines,
        "rating": candidate.rating,
        "cost_for_two": candidate.cost_for_two,
        "budget_band": candidate.budget_band,
        "city": candidate.city,
        "area": candidate.area,
        "attributes": _selected_attributes(candidate),
    }


def _selected_attributes(candidate: RestaurantRecord) -> dict[str, Any]:
    keys = (
        "rest_type",
        "online_order",
        "book_table",
        "dish_liked",
        "listed_in(type)",
        "votes",
    )
    return {key: candidate.raw_attributes[key] for key in keys if key in candidate.raw_attributes}

