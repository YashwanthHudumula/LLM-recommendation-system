"""Consistent structured-enough logging for command-line research runs."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once with timestamps and module names."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )

