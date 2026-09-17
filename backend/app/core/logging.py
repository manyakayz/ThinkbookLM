from __future__ import annotations
"""Minimal logging setup, applied once at application startup."""

import logging


def configure_logging(app_env: str) -> None:
    level = logging.DEBUG if app_env == "development" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

