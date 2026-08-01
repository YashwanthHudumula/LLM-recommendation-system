"""RQ3 rank correlation and pre-registered scenario classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import spearmanr

RQ3Scenario = Literal["concordant", "independent", "inverse"]


@dataclass(frozen=True)
class CorrelationResult:
    rho: float
    p_value: float
    scenario: RQ3Scenario


def classify_scenario(
    rho: float,
    p_value: float,
    *,
    alpha: float = 0.05,
    minimum_effect: float = 0.20,
) -> RQ3Scenario:
    """Classify only statistically credible, non-trivial effects as concordant/inverse."""
    if not -1 <= rho <= 1 or not 0 <= p_value <= 1:
        raise ValueError("Invalid correlation inputs")
    if p_value >= alpha or abs(rho) < minimum_effect:
        return "independent"
    return "concordant" if rho > 0 else "inverse"


def spearman_fairness_scenario(
    user_side_harm: np.ndarray,
    item_side_harm: np.ndarray,
    *,
    alpha: float = 0.05,
    minimum_effect: float = 0.20,
) -> CorrelationResult:
    """Correlate condition rankings after orienting both inputs so higher means worse."""
    left = np.asarray(user_side_harm, dtype=float)
    right = np.asarray(item_side_harm, dtype=float)
    if left.shape != right.shape or left.ndim != 1 or left.size < 3:
        raise ValueError("Spearman comparison needs equal 1D arrays with at least three conditions")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise ValueError("Spearman inputs must be finite")
    result = spearmanr(left, right)
    rho, p_value = float(result.statistic), float(result.pvalue)
    if np.isnan(rho):
        raise ValueError("Spearman correlation is undefined for constant ranks")
    return CorrelationResult(
        rho,
        p_value,
        classify_scenario(rho, p_value, alpha=alpha, minimum_effect=minimum_effect),
    )

