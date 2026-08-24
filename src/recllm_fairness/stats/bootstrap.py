"""Persona-cluster bootstrap for aggregate exposure statistics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BootstrapResult:
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    replicates: np.ndarray


def persona_bootstrap(
    data: pd.DataFrame,
    statistic: Callable[[pd.DataFrame], float],
    *,
    persona_column: str = "persona_id",
    n_resamples: int = 2_000,
    confidence_level: float = 0.95,
    seed: int = 0,
) -> BootstrapResult:
    """Resample persona clusters, retaining every query/repeat belonging to each draw."""
    if persona_column not in data:
        raise ValueError(f"Missing persona column: {persona_column}")
    personas = data[persona_column].drop_duplicates().to_numpy()
    if personas.size < 2:
        raise ValueError("Persona bootstrap needs at least two distinct personas")
    if n_resamples < 1 or not 0 < confidence_level < 1:
        raise ValueError("Invalid bootstrap settings")
    grouped = {persona: group for persona, group in data.groupby(persona_column, sort=False)}
    rng = np.random.default_rng(seed)
    values = np.empty(n_resamples, dtype=float)
    for index in range(n_resamples):
        draw = rng.choice(personas, size=len(personas), replace=True)
        chunks: list[pd.DataFrame] = []
        for instance, persona in enumerate(draw):
            chunk = grouped[persona].copy()
            chunk["__bootstrap_persona_instance"] = instance
            chunks.append(chunk)
        values[index] = statistic(pd.concat(chunks, ignore_index=True))
    alpha = 1 - confidence_level
    lower, upper = np.quantile(values, [alpha / 2, 1 - alpha / 2])
    return BootstrapResult(
        estimate=float(statistic(data)),
        lower=float(lower),
        upper=float(upper),
        confidence_level=confidence_level,
        replicates=values,
    )
