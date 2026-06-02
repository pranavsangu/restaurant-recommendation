"""Canonical restaurant records used by retrieval and presentation layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RestaurantRecord:
    """Normalized restaurant row with dataset facts owned by code."""

    id: str
    name: str
    city: str | None
    area: str | None
    cuisines: list[str]
    cost_for_two: int | None
    budget_band: str | None
    rating: float | None
    raw_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "area": self.area,
            "cuisines": self.cuisines,
            "cost_for_two": self.cost_for_two,
            "budget_band": self.budget_band,
            "rating": self.rating,
            "raw_attributes": self.raw_attributes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RestaurantRecord:
        return cls(
            id=str(payload["id"]),
            name=str(payload["name"]),
            city=_optional_str(payload.get("city")),
            area=_optional_str(payload.get("area")),
            cuisines=[str(value) for value in payload.get("cuisines", [])],
            cost_for_two=_optional_int(payload.get("cost_for_two")),
            budget_band=_optional_str(payload.get("budget_band")),
            rating=_optional_float(payload.get("rating")),
            raw_attributes=dict(payload.get("raw_attributes", {})),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)

