"""Hugging Face dataset loading and normalized cache orchestration."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

from zomato_ai.config import AppSettings
from zomato_ai.data_ingestion.cache import CacheError, load_cached_records, write_cached_records
from zomato_ai.data_ingestion.normalizer import NormalizationResult, normalize_rows
from zomato_ai.domain import RestaurantRecord

DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"
LOGGER = logging.getLogger(__name__)


class DatasetLoadError(RuntimeError):
    """Raised when the source dataset cannot be loaded."""


def load_restaurant_records(
    settings: AppSettings, *, use_cache: bool = True
) -> list[RestaurantRecord]:
    """Load normalized records from cache when possible, otherwise from Hugging Face."""

    if use_cache:
        try:
            cached = load_cached_records(settings.dataset_cache_dir)
        except CacheError as exc:
            LOGGER.warning("Ignoring invalid normalized cache: %s", exc)
        else:
            if cached is not None:
                LOGGER.info("Loaded %s normalized restaurant records from cache", len(cached))
                return cached

    result = load_and_normalize_dataset()
    LOGGER.info(
        "Normalized %s/%s restaurant rows; skipped=%s",
        result.report.normalized_rows,
        result.report.total_rows,
        len(result.report.skipped_rows),
    )
    if result.report.skipped_rows:
        LOGGER.warning("First skipped row: %s", result.report.skipped_rows[0])

    if use_cache:
        cache_file = write_cached_records(settings.dataset_cache_dir, result.records)
        LOGGER.info("Wrote normalized restaurant cache to %s", cache_file)

    return result.records


def refresh_restaurant_cache(settings: AppSettings) -> NormalizationResult:
    """Reload the source dataset, normalize it, and overwrite the local cache."""

    result = load_and_normalize_dataset()
    cache_file = write_cached_records(settings.dataset_cache_dir, result.records)
    LOGGER.info(
        "Refreshed normalized cache at %s with %s/%s rows; skipped=%s",
        cache_file,
        result.report.normalized_rows,
        result.report.total_rows,
        len(result.report.skipped_rows),
    )
    return result


def load_and_normalize_dataset() -> NormalizationResult:
    return normalize_rows(load_raw_dataset_rows())


def load_raw_dataset_rows() -> Iterable[Mapping[str, Any]]:
    """Yield rows from the configured Hugging Face dataset.

    The import is local so Phase 0/1 unit tests can run without importing the
    optional dependency unless this loader is actually used.
    """

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise DatasetLoadError(
            "The 'datasets' package is required to load Hugging Face data. "
            'Install project dependencies with: python -m pip install -e ".[dev]"'
        ) from exc

    try:
        dataset = load_dataset(DATASET_NAME)
    except Exception as exc:  # pragma: no cover - depends on remote service.
        raise DatasetLoadError(f"failed to load Hugging Face dataset {DATASET_NAME}") from exc

    split_name = "train" if "train" in dataset else next(iter(dataset.keys()), None)
    if split_name is None:
        raise DatasetLoadError(f"dataset {DATASET_NAME} does not contain any splits")

    for row in dataset[split_name]:
        yield dict(row)
