import pytest

from zomato_ai.data_ingestion.cache import (
    CacheError,
    cache_path,
    load_cached_records,
    write_cached_records,
)
from zomato_ai.domain import RestaurantRecord


def test_cache_roundtrip(tmp_path) -> None:
    records = [
        RestaurantRecord(
            id="r1",
            name="Cafe One",
            city="Delhi",
            area="Connaught Place",
            cuisines=["Cafe"],
            cost_for_two=700,
            budget_band="medium",
            rating=4.2,
            raw_attributes={"source": "fixture"},
        )
    ]

    path = write_cached_records(tmp_path, records)
    loaded = load_cached_records(tmp_path)

    assert path == cache_path(tmp_path)
    assert loaded == records


def test_missing_cache_returns_none(tmp_path) -> None:
    assert load_cached_records(tmp_path) is None


def test_corrupt_cache_raises_clear_error(tmp_path) -> None:
    cache_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    cache_path(tmp_path).write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(CacheError, match="failed to read normalized cache"):
        load_cached_records(tmp_path)

