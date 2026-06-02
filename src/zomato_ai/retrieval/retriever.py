"""Deterministic filtering, sorting, and candidate capping."""

from __future__ import annotations

import re
from dataclasses import dataclass

from zomato_ai.domain import RestaurantRecord, UserPreferences
from zomato_ai.retrieval.index import RestaurantIndex


@dataclass(frozen=True)
class RetrievalResult:
    """Candidates returned by deterministic retrieval."""

    candidates: list[RestaurantRecord]
    total_matches: int
    max_candidates: int
    filters_applied: dict[str, object]

    @property
    def is_truncated(self) -> bool:
        return self.total_matches > len(self.candidates)

    @property
    def is_empty(self) -> bool:
        return not self.candidates


class CandidateRetriever:
    """Pure deterministic candidate retrieval over normalized rows."""

    def __init__(self, index: RestaurantIndex, *, max_candidates: int) -> None:
        if max_candidates <= 0:
            raise ValueError("max_candidates must be greater than zero")
        self.index = index
        self.max_candidates = max_candidates

    def retrieve(self, preferences: UserPreferences) -> RetrievalResult:
        matches = [
            record
            for record in self.index.records
            if _matches_location(record, preferences.location)
            and _matches_budget(record, preferences.budget)
            and _matches_cuisines(record, preferences.cuisines)
            and _matches_min_rating(record, preferences.min_rating)
        ]
        sorted_matches = sorted(matches, key=_sort_key)
        capped = sorted_matches[: self.max_candidates]

        return RetrievalResult(
            candidates=capped,
            total_matches=len(sorted_matches),
            max_candidates=self.max_candidates,
            filters_applied=_filters_applied(preferences),
        )


def deterministic_rank(records: list[RestaurantRecord]) -> list[RestaurantRecord]:
    """Rank records without model help using the same stable ordering as retrieval."""

    return sorted(records, key=_sort_key)


def _matches_location(record: RestaurantRecord, location: str | None) -> bool:
    if location is None:
        return True
    needle = _normalize_search_text(location)
    haystacks = [
        record.city,
        record.area,
        _raw_value(record, "listed_in(city)"),
        _raw_value(record, "location"),
    ]
    return any(needle in _normalize_search_text(value) for value in haystacks if value)


def _matches_budget(record: RestaurantRecord, budget: str | None) -> bool:
    if budget is None:
        return True
    return record.budget_band == budget


def _matches_cuisines(record: RestaurantRecord, cuisines: list[str]) -> bool:
    if not cuisines:
        return True
    record_cuisines = {_normalize_search_text(cuisine) for cuisine in record.cuisines}
    requested = {_normalize_search_text(cuisine) for cuisine in cuisines}
    return bool(record_cuisines.intersection(requested))


def _matches_min_rating(record: RestaurantRecord, min_rating: float | None) -> bool:
    if min_rating is None:
        return True
    return record.rating is not None and record.rating >= min_rating


def _sort_key(record: RestaurantRecord) -> tuple[float, int, str, str]:
    rating_key = -(record.rating if record.rating is not None else -1.0)
    cost_key = record.cost_for_two if record.cost_for_two is not None else 10**12
    return (rating_key, cost_key, record.name.lower(), record.id)


def _filters_applied(preferences: UserPreferences) -> dict[str, object]:
    return {
        "location": preferences.location,
        "budget": preferences.budget,
        "cuisines": preferences.cuisines,
        "min_rating": preferences.min_rating,
        "extras_text": preferences.extras_text,
        "top_k": preferences.top_k,
    }


def _raw_value(record: RestaurantRecord, key: str) -> str | None:
    value = record.raw_attributes.get(key)
    if value is None:
        return None
    return str(value)


def _normalize_search_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())
