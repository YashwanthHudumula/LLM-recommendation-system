"""Small, explicit YAML configuration composition.

Hydra would add substantial runtime machinery for four static files. This loader provides
deep merging and path resolution while keeping every experiment constant reviewable.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge mappings without mutating either input."""
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_yaml(path: Path) -> dict[str, Any]:
    """Load one YAML mapping, failing clearly on a non-mapping document."""
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise TypeError(f"Expected a YAML mapping in {path}")
    return value


def load_config(config_dir: str | Path, override: str | Path | None = None) -> dict[str, Any]:
    """Compose the project's four canonical configs and an optional override."""
    root = Path(config_dir)
    result: dict[str, Any] = {}
    for name in ("base.yaml", "personas.yaml", "models.yaml", "datasets.yaml"):
        path = root / name
        if not path.exists():
            raise FileNotFoundError(f"Missing required configuration file: {path}")
        result = deep_merge(result, load_yaml(path))
    if override is not None:
        result = deep_merge(result, load_yaml(Path(override)))
    return result

