"""Deterministic condition-specific seeds."""

from __future__ import annotations

import hashlib


def condition_seed(base_seed: int, *parts: object) -> int:
    """Derive a stable 32-bit seed independent of Python hash randomization."""
    payload = "|".join([str(base_seed), *(str(part) for part in parts)]).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")

