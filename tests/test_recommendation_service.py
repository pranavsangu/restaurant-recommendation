import pytest

from zomato_ai.config import load_settings
from zomato_ai.domain import RestaurantRecord, UserPreferences
from zomato_ai.orchestration import RecommendationError, RecommendationService


def restaurant(
    restaurant_id: str,
    name: str,
    *,
    city: str = "Bangalore",
    area: str = "Indiranagar",
    cuisines: list[str] | None = None,
    cost_for_two: int | None = 800,
    budget_band: str | None = "medium",
    rating: float | None = 4.0,
) -> RestaurantRecord:
    return RestaurantRecord(
        id=restaurant_id,
        name=name,
        city=city,
        area=area,
        cuisines=cuisines or ["Italian"],
        cost_for_two=cost_for_two,
        budget_band=budget_band,
        rating=rating,
        raw_attributes={"location": area, "listed_in(city)": city},
    )


def test_recommendation_service_returns_deterministic_fallback_response() -> None:
    service = RecommendationService(
        settings=load_settings({"MAX_CANDIDATES": "10", "TOP_K_OUTPUT": "2"}),
        record_loader=lambda _settings: [
            restaurant("a", "Alpha", rating=4.8, cost_for_two=900),
            restaurant("b", "Bravo", rating=4.9, cost_for_two=1200),
            restaurant("c", "Charlie", rating=4.1, cost_for_two=700),
        ],
    )

    response = service.recommend(
        {
            "location": "Bangalore",
            "budget": "medium",
            "cuisines": ["Italian"],
            "min_rating": 4.0,
        }
    )

    assert [item.restaurant_id for item in response.recommendations] == ["b", "a"]
    assert response.recommendations[0].name == "Bravo"
    assert response.recommendations[0].rating == 4.9
    assert response.recommendations[0].estimated_cost == 1200
    assert "rated 4.9" in response.recommendations[0].explanation
    assert response.metadata.candidate_count == 3
    assert response.metadata.returned_count == 2
    assert response.metadata.top_k == 2
    assert response.metadata.degraded is True
    assert response.metadata.mode == "deterministic_fallback"


def test_recommendation_service_respects_top_k() -> None:
    service = RecommendationService(
        settings=load_settings({"MAX_CANDIDATES": "10", "TOP_K_OUTPUT": "5"}),
        record_loader=lambda _settings: [
            restaurant("a", "Alpha", rating=4.8),
            restaurant("b", "Bravo", rating=4.7),
            restaurant("c", "Charlie", rating=4.6),
        ],
    )

    response = service.recommend(UserPreferences(top_k=1))

    assert len(response.recommendations) == 1
    assert response.metadata.top_k == 1


def test_recommendation_service_returns_no_match_response() -> None:
    service = RecommendationService(
        settings=load_settings({"MAX_CANDIDATES": "10", "TOP_K_OUTPUT": "3"}),
        record_loader=lambda _settings: [
            restaurant("a", "Alpha", city="Bangalore", area="Indiranagar"),
        ],
    )

    response = service.recommend({"location": "Delhi"})

    assert response.recommendations == []
    assert response.message == "No restaurants matched the provided filters."
    assert response.metadata.candidate_count == 0
    assert response.metadata.returned_count == 0
    assert response.metadata.filters_applied["location"] == "Delhi"


def test_recommendation_service_validates_input_against_runtime_limits() -> None:
    service = RecommendationService(
        settings=load_settings({"MAX_CANDIDATES": "2", "TOP_K_OUTPUT": "1"}),
        record_loader=lambda _settings: [],
    )

    with pytest.raises(RecommendationError, match="top_k"):
        service.recommend({"top_k": 3})


def test_recommendation_service_builds_index_once() -> None:
    calls = 0

    def loader(_settings):
        nonlocal calls
        calls += 1
        return [restaurant("a", "Alpha")]

    service = RecommendationService(
        settings=load_settings({"MAX_CANDIDATES": "10", "TOP_K_OUTPUT": "1"}),
        record_loader=loader,
    )

    service.recommend({})
    service.recommend({})

    assert calls == 1


def test_recommendation_service_returns_known_locations() -> None:
    service = RecommendationService(
        settings=load_settings({"MAX_CANDIDATES": "10", "TOP_K_OUTPUT": "1"}),
        record_loader=lambda _settings: [
            restaurant("a", "Alpha", area="Indiranagar"),
            restaurant("b", "Bravo", area="Banashankari"),
            restaurant("c", "Charlie", area=""),
        ],
    )

    assert service.known_locations() == ["Banashankari", "Indiranagar"]


class FakeLLMClient:
    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = 0

    def complete(self, messages):
        self.calls += 1
        assert "candidates" in messages[1]["content"]
        return self.output


def test_recommendation_service_uses_groq_ranked_output_when_enabled() -> None:
    fake_llm = FakeLLMClient(
        """
        {
          "recommendations": [
            {"restaurant_id": "a", "rank": 1, "explanation": "Best fit from supplied facts."}
          ]
        }
        """
    )
    service = RecommendationService(
        settings=load_settings(
            {
                "MAX_CANDIDATES": "10",
                "TOP_K_OUTPUT": "2",
                "LLM_API_KEY": "test-key",
                "LLM_MODEL": "llama-test",
            }
        ),
        record_loader=lambda _settings: [
            restaurant("a", "Alpha", rating=4.2),
            restaurant("b", "Bravo", rating=4.9),
        ],
        llm_client=fake_llm,
    )

    response = service.recommend({})

    assert fake_llm.calls == 1
    assert response.metadata.mode == "groq"
    assert response.metadata.degraded is False
    assert [item.restaurant_id for item in response.recommendations] == ["a", "b"]
    assert response.recommendations[0].explanation == "Best fit from supplied facts."


def test_recommendation_service_falls_back_when_llm_output_is_invalid() -> None:
    service = RecommendationService(
        settings=load_settings(
            {
                "MAX_CANDIDATES": "10",
                "TOP_K_OUTPUT": "1",
                "LLM_API_KEY": "test-key",
                "LLM_MODEL": "llama-test",
            }
        ),
        record_loader=lambda _settings: [
            restaurant("a", "Alpha", rating=4.2),
            restaurant("b", "Bravo", rating=4.9),
        ],
        llm_client=FakeLLMClient("not-json"),
    )

    response = service.recommend({})

    assert response.metadata.mode == "deterministic_fallback"
    assert response.metadata.degraded is True
    assert [item.restaurant_id for item in response.recommendations] == ["b"]
