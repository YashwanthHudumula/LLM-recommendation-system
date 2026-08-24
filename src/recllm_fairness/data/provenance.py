"""Streaming checksum verification shared by every raw dataset archive."""

from __future__ import annotations

import hashlib
from pathlib import Path


def md5_checksum(path: str | Path) -> str:
    """Return a streaming MD5 for compatibility with publishers' legacy manifests."""
    digest = hashlib.md5(usedforsecurity=False)
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: str | Path, expected_md5: str) -> None:
    """Fail loudly when an archive differs from its frozen publisher checksum."""
    actual = md5_checksum(path)
    if actual.casefold() != expected_md5.casefold():
        raise ValueError(f"Checksum mismatch for {path}: expected {expected_md5}, got {actual}")
