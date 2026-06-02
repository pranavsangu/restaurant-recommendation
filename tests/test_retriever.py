from zomato_ai.domain import RestaurantRecord, UserPreferences
from zomato_ai.retrieval import CandidateRetriever, RestaurantIndex, deterministic_rank


def restaurant(
    restaurant_id: str,
    name: str,
    *,
    city: str | None = "Bangalore",
    area: str | None = "Indiranagar",
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
        raw_attributes={"location": area or "", "listed_in(city)": city or ""},
    )


def test_retriever_applies_hard_filters() -> None:
    index = RestaurantIndex.build(
        [
            restaurant("a", "Match", cuisines=["Italian"], budget_band="medium", rating=4.4),
            restaurant(
                "b",
                "Wrong Cuisine",
                cuisines=["Chinese"],
                budget_band="medium",
                rating=4.5,
            ),
            restaurant("c", "Wrong Budget", cuisines=["Italian"], budget_band="high", rating=4.6),
            restaurant("d", "Too Low", cuisines=["Italian"], budget_band="medium", rating=3.2),
            restaurant(
                "e",
                "Wrong City",
                city="Delhi",
                area="Saket",
                cuisines=["Italian"],
                rating=4.7,
            ),
        ]
    )
    retriever = CandidateRetriever(index, max_candidates=10)

    result = retriever.retrieve(
        UserPreferences(
            location="Bangalore",
            budget="medium",
            cuisines=["Italian"],
            min_rating=4.0,
        )
    )

    assert [candidate.id for candidate in result.candidates] == ["a"]
    assert result.total_matches == 1


def test_retriever_excludes_unknown_rating_only_when_min_rating_filter_is_set() -> None:
    index = RestaurantIndex.build(
        [
            restaurant("a", "Rated", rating=4.2),
            restaurant("b", "Unknown Rating", rating=None),
        ]
    )
    retriever = CandidateRetriever(index, max_candidates=10)

    without_filter = retriever.retrieve(UserPreferences())
    with_filter = retriever.retrieve(UserPreferences(min_rating=4.0))

    assert {candidate.id for candidate in without_filter.candidates} == {"a", "b"}
    assert [candidate.id for candidate in with_filter.candidates] == ["a"]


def test_retriever_excludes_unknown_cost_only_when_budget_filter_is_set() -> None:
    index = RestaurantIndex.build(
        [
            restaurant("a", "Known Cost", budget_band="medium", cost_for_two=900),
            restaurant("b", "Unknown Cost", budget_band=None, cost_for_two=None),
        ]
    )
    retriever = CandidateRetriever(index, max_candidates=10)

    without_filter = retriever.retrieve(UserPreferences())
    with_filter = retriever.retrieve(UserPreferences(budget="medium"))

    assert {candidate.id for candidate in without_filter.candidates} == {"a", "b"}
    assert [candidate.id for candidate in with_filter.candidates] == ["a"]


def test_retriever_sorts_deterministically_before_capping() -> None:
    index = RestaurantIndex.build(
        [
            restaurant("c", "Charlie", rating=4.5, cost_for_two=900),
            restaurant("a", "Alpha", rating=4.8, cost_for_two=1200),
            restaurant("b", "Bravo", rating=4.8, cost_for_two=800),
            restaurant("d", "Delta", rating=4.8, cost_for_two=800),
        ]
    )
    retriever = CandidateRetriever(index, max_candidates=3)

    result = retriever.retrieve(UserPreferences())

    assert [candidate.id for candidate in result.candidates] == ["b", "d", "a"]
    assert result.total_matches == 4
    assert result.is_truncated is True


def test_retriever_returns_empty_no_match_result() -> None:
    index = RestaurantIndex.build([restaurant("a", "Only Place", city="Bangalore")])
    retriever = CandidateRetriever(index, max_candidates=10)

    result = retriever.retrieve(UserPreferences(location="Delhi"))

    assert result.candidates == []
    assert result.total_matches == 0
    assert result.is_empty is True
    assert result.filters_applied["location"] == "Delhi"


def test_index_deduplicates_by_id() -> None:
    index = RestaurantIndex.build(
        [
            restaurant("a", "First"),
            restaurant("a", "Duplicate"),
        ]
    )

    assert len(index) == 1
    assert index.get("a").name == "First"


def test_deterministic_rank_uses_same_ordering() -> None:
    records = [
        restaurant("a", "Alpha", rating=4.0, cost_for_two=500),
        restaurant("b", "Bravo", rating=4.5, cost_for_two=1000),
    ]

    assert [record.id for record in deterministic_rank(records)] == ["b", "a"]
