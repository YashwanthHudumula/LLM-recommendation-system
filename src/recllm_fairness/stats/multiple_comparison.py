"""Dependency-light Benjamini-Hochberg false-discovery-rate correction."""

from __future__ import annotations

import numpy as np


def benjamini_hochberg(
    p_values: list[float] | np.ndarray, *, alpha: float = 0.05
) -> tuple[np.ndarray, np.ndarray]:
    """Return rejection flags and monotone BH-adjusted p-values in original order."""
    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1 or values.size == 0 or np.any((values < 0) | (values > 1)):
        raise ValueError("p-values must be a non-empty 1D sequence in [0, 1]")
    order = np.argsort(values)
    ranked = values[order]
    m = len(values)
    adjusted_ranked = ranked * m / np.arange(1, m + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1].clip(max=1.0)
    adjusted = np.empty(m, dtype=float)
    adjusted[order] = adjusted_ranked
    return adjusted <= alpha, adjusted
