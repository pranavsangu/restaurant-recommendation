"""Logging setup for application entrypoints."""

from __future__ import annotations

import logging

from zomato_ai.config.settings import AppSettings


def configure_logging(settings: AppSettings) -> None:
    """Configure a small, consistent logging baseline."""

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
