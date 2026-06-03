from zomato_ai.data_ingestion.normalizer import (
    map_budget_band,
    normalize_row,
    normalize_rows,
    parse_cost,
    parse_cuisines,
    parse_rating,
)


def test_normalize_row_maps_common_zomato_columns() -> None:
    record = normalize_row(
        {
            "Restaurant ID": "abc-123",
            "Restaurant Name": "  The Test Kitchen ",
            "listed_in(city)": "Bangalore",
            "Locality": "Indiranagar",
            "Cuisines": "North Indian, Chinese / Cafe",
            "approx_cost(for two people)": "₹1,200",
            "Aggregate rating": "4.3/5",
        }
    )

    assert record.id == "abc-123"
    assert record.name == "The Test Kitchen"
    assert record.city == "Bangalore"
    assert record.area == "Indiranagar"
    assert record.cuisines == ["North Indian", "Chinese", "Cafe"]
    assert record.cost_for_two == 1200
    assert record.budget_band == "medium"
    assert record.rating == 4.3


def test_normalize_row_creates_stable_hash_id_without_source_id() -> None:
    row = {
        "Restaurant Name": "Same Place",
        "City": "Delhi",
        "Cuisines": "Italian",
    }

    first = normalize_row(row)
    second = normalize_row(dict(reversed(list(row.items()))), row_index=99)

    assert first.id == second.id


def test_normalize_rows_skips_missing_restaurant_name() -> None:
    result = normalize_rows(
        [
            {"Restaurant Name": "Valid", "City": "Delhi"},
            {"City": "Delhi", "Cuisines": "Chinese"},
        ]
    )

    assert len(result.records) == 1
    assert result.report.total_rows == 2
    assert result.report.normalized_rows == 1
    assert result.report.skipped_rows[0].reason == "missing restaurant name"


def test_parse_rating_handles_malformed_values() -> None:
    assert parse_rating("4.1") == 4.1
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating("NEW") is None
    assert parse_rating("9.9") is None
    assert parse_rating(None) is None


def test_parse_cost_handles_currency_and_bad_values() -> None:
    assert parse_cost("₹1,500 for two") == 1500
    assert parse_cost("1,200") == 1200
    assert parse_cost("not available") is None
    assert parse_cost(None) is None


def test_parse_cuisines_splits_and_deduplicates() -> None:
    assert parse_cuisines("Italian, Cafe / Cafe | Bakery") == ["Italian", "Cafe", "Bakery"]


def test_budget_band_mapping() -> None:
    assert map_budget_band(None) is None
    assert map_budget_band(400) == "low"
    assert map_budget_band(900) == "medium"
    assert map_budget_band(2200) == "high"
