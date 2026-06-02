"""Normalize raw dataset rows into canonical restaurant records."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from zomato_ai.domain import RestaurantRecord

ID_ALIASES = (
    "restaurant_id",
    "restaurant id",
    "id",
)
NAME_ALIASES = (
    "restaurant_name",
    "restaurant name",
    "name",
    "restaurant",
)
CITY_ALIASES = (
    "city",
    "location_city",
)
AREA_ALIASES = (
    "area",
    "locality",
    "locality verbose",
    "location",
)
CUISINE_ALIASES = (
    "cuisines",
    "cuisine",
)
COST_ALIASES = (
    "average_cost_for_two",
    "average cost for two",
    "cost_for_two",
    "cost for two",
    "cost",
    "price",
)
RATING_ALIASES = (
    "aggregate_rating",
    "aggregate rating",
    "rating",
    "rate",
)

LOW_BUDGET_MAX = 500
MEDIUM_BUDGET_MAX = 1500


@dataclass(frozen=True)
class SkippedRow:
    row_index: int
    reason: str


@dataclass(frozen=True)
class NormalizationReport:
    total_rows: int
    normalized_rows: int
    skipped_rows: tuple[SkippedRow, ...] = field(default_factory=tuple)
    source_columns: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NormalizationResult:
    records: list[RestaurantRecord]
    report: NormalizationReport


def normalize_rows(rows: Iterable[Mapping[str, Any]]) -> NormalizationResult:
    """Normalize raw rows and skip only rows that cannot be safely displayed."""

    records: list[RestaurantRecord] = []
    skipped: list[SkippedRow] = []
    source_columns: set[str] = set()
    total_rows = 0

    for row_index, row in enumerate(rows):
        total_rows += 1
        normalized_row = dict(row)
        source_columns.update(str(key) for key in normalized_row)

        try:
            record = normalize_row(normalized_row, row_index=row_index)
        except ValueError as exc:
            skipped.append(SkippedRow(row_index=row_index, reason=str(exc)))
            continue

        records.append(record)

    return NormalizationResult(
        records=records,
        report=NormalizationReport(
            total_rows=total_rows,
            normalized_rows=len(records),
            skipped_rows=tuple(skipped),
            source_columns=tuple(sorted(source_columns)),
        ),
    )


def normalize_row(row: Mapping[str, Any], row_index: int = 0) -> RestaurantRecord:
    """Normalize one raw dataset row.

    Missing restaurant names are fatal because the final recommendation cannot
    be shown or validated safely without a display name.
    """

    name = _clean_text(_pick_value(row, NAME_ALIASES))
    if name is None:
        raise ValueError("missing restaurant name")

    cost_for_two = parse_cost(_pick_value(row, COST_ALIASES))
    rating = parse_rating(_pick_value(row, RATING_ALIASES))

    return RestaurantRecord(
        id=_stable_id(row),
        name=name,
        city=_clean_text(_pick_value(row, CITY_ALIASES)),
        area=_clean_text(_pick_value(row, AREA_ALIASES)),
        cuisines=parse_cuisines(_pick_value(row, CUISINE_ALIASES)),
        cost_for_two=cost_for_two,
        budget_band=map_budget_band(cost_for_two),
        rating=rating,
        raw_attributes=_clean_raw_attributes(row),
    )


def parse_rating(value: Any) -> float | None:
    text = _clean_text(value)
    if text is None:
        return None

    lowered = text.lower()
    if lowered in {"new", "nan", "none", "null", "-", "--", "not rated"}:
        return None

    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None

    rating = float(match.group(0))
    if 0 <= rating <= 5:
        return rating
    return None


def parse_cost(value: Any) -> int | None:
    text = _clean_text(value)
    if text is None:
        return None

    lowered = text.lower()
    if lowered in {"nan", "none", "null", "-", "--", "not available"}:
        return None

    match = re.search(r"\d[\d,.\s]*", text)
    if not match:
        return None

    numeric = re.sub(r"[^\d.]", "", match.group(0))
    if not numeric:
        return None

    try:
        return int(float(numeric))
    except ValueError:
        return None


def parse_cuisines(value: Any) -> list[str]:
    text = _clean_text(value)
    if text is None:
        return []

    pieces = re.split(r"[,|/;]+", text)
    cuisines = []
    seen = set()
    for piece in pieces:
        cleaned = " ".join(piece.strip().split())
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        cuisines.append(cleaned)
    return cuisines


def map_budget_band(cost_for_two: int | None) -> str | None:
    if cost_for_two is None:
        return None
    if cost_for_two <= LOW_BUDGET_MAX:
        return "low"
    if cost_for_two <= MEDIUM_BUDGET_MAX:
        return "medium"
    return "high"


def _stable_id(row: Mapping[str, Any]) -> str:
    source_id = _clean_text(_pick_value(row, ID_ALIASES))
    if source_id is not None:
        return source_id

    sorted_items = sorted(row.items(), key=lambda item: str(item[0]))
    canonical_payload = json.dumps(
        {str(key): _json_safe(value) for key, value in sorted_items},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()[:16]
    return f"row-{digest}"


def _pick_value(row: Mapping[str, Any], aliases: tuple[str, ...]) -> Any:
    normalized_aliases = {_normalize_key(alias) for alias in aliases}
    for key, value in row.items():
        if _normalize_key(str(key)) in normalized_aliases:
            return value
    return None


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", key.strip().lower()).strip()


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _clean_raw_attributes(row: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in row.items():
        if value is None:
            continue
        if isinstance(value, float) and value != value:
            continue
        cleaned[str(key)] = _json_safe(value)
    return cleaned


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)
