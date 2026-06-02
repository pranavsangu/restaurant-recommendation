from fastapi.testclient import TestClient

from zomato_ai.api.app import create_app
from zomato_ai.domain import RecommendationMetadata, RecommendationResponse


class FakeRecommendationService:
    _index = None

    def recommend(self, payload):
        return RecommendationResponse(
            recommendations=[],
            metadata=RecommendationMetadata(
                candidate_count=0,
                total_matches=0,
                returned_count=0,
                max_candidates=30,
                top_k=5,
                degraded=True,
                mode="deterministic_fallback",
                filters_applied=payload,
            ),
            message="No restaurants matched the provided filters.",
        )


def test_frontend_page_loads() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Zomato AI" in response.text
    assert "/v1/recommendations" in response.text


def test_recommendations_endpoint_returns_response_model() -> None:
    app = create_app()
    app.state.recommendation_service = FakeRecommendationService()
    client = TestClient(app)

    response = client.post("/v1/recommendations", json={"location": "Nowhere"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"] == []
    assert payload["metadata"]["filters_applied"]["location"] == "Nowhere"

