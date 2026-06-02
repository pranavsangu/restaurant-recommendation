"""In-memory restaurant index for deterministic retrieval."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from zomato_ai.domain import RestaurantRecord


@dataclass(frozen=True)
class RestaurantIndex:
    """Small in-memory store keyed by restaurant ID."""

    records: tuple[RestaurantRecord, ...]
    by_id: dict[str, RestaurantRecord]

    @classmethod
    def build(cls, records: Iterable[RestaurantRecord]) -> RestaurantIndex:
        deduped: dict[str, RestaurantRecord] = {}
        for record in records:
            deduped.setdefault(record.id, record)
        return cls(records=tuple(deduped.values()), by_id=deduped)

    def get(self, restaurant_id: str) -> RestaurantRecord | None:
        return self.by_id.get(restaurant_id)

    def __len__(self) -> int:
        return len(self.records)

