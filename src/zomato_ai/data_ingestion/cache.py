"""Local JSONL cache for normalized restaurant records."""

from __future__ import annotations

import json
from pathlib import Path

from zomato_ai.domain import RestaurantRecord

CACHE_FILENAME = "restaurants.normalized.jsonl"


class CacheError(RuntimeError):
    """Raised when a cache file exists but cannot be parsed."""


def cache_path(cache_dir: str | Path) -> Path:
    return Path(cache_dir) / CACHE_FILENAME


def load_cached_records(cache_dir: str | Path) -> list[RestaurantRecord] | None:
    path = cache_path(cache_dir)
    if not path.exists():
        return None

    records: list[RestaurantRecord] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                records.append(RestaurantRecord.from_dict(json.loads(line)))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise CacheError(f"failed to read normalized cache at {path}") from exc

    return records


def write_cached_records(cache_dir: str | Path, records: list[RestaurantRecord]) -> Path:
    path = cache_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), sort_keys=True))
            handle.write("\n")

    return path
