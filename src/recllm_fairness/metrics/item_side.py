"""Pure aggregate catalog-exposure metrics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _nonnegative(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError("Metric input must be a non-empty one-dimensional sequence")
    if np.any(array < 0) or not np.all(np.isfinite(array)):
        raise ValueError("Exposure values must be finite and non-negative")
    return array


def gini_index(exposures: Sequence[float]) -> float:
    """Gini over every catalog item, including zero-exposure items."""
    values = np.sort(_nonnegative(exposures))
    if values.sum() == 0:
        return 0.0
    n = values.size
    return float((2 * np.dot(np.arange(1, n + 1), values) / (n * values.sum())) - (n + 1) / n)


def hhi(exposures: Sequence[float]) -> float:
    values = _nonnegative(exposures)
    return 0.0 if values.sum() == 0 else float(np.square(values / values.sum()).sum())


def normalized_hhi(exposures: Sequence[float]) -> float:
    values = _nonnegative(exposures)
    if values.size == 1:
        return 1.0 if values[0] > 0 else 0.0
    raw = hhi(values.tolist())
    return float((raw - 1 / values.size) / (1 - 1 / values.size))


def average_recommendation_popularity(
    recommended_item_ids: Sequence[str], popularity: Mapping[str, float]
) -> float:
    """ARP: mean configured popularity signal (normally interaction count) at K."""
    if not recommended_item_ids:
        return float("nan")
    missing = set(recommended_item_ids) - set(popularity)
    if missing:
        raise KeyError(f"Popularity missing for items: {sorted(missing)[:5]}")
    return float(np.mean([popularity[item] for item in recommended_item_ids]))


def catalog_coverage(recommended_item_ids: Sequence[str], catalog_item_ids: Sequence[str]) -> float:
    catalog = set(catalog_item_ids)
    if not catalog:
        raise ValueError("Catalog coverage needs a non-empty catalog")
    return len(set(recommended_item_ids) & catalog) / len(catalog)


def long_tail_coverage(recommended_item_ids: Sequence[str], tail_item_ids: Sequence[str]) -> float:
    tail = set(tail_item_ids)
    if not tail:
        raise ValueError("Long-tail coverage needs a non-empty tail")
    return len(set(recommended_item_ids) & tail) / len(tail)


def group_unfairness(
    recommendation_group_counts: Mapping[str, float],
    reference_group_counts: Mapping[str, float],
) -> dict[str, float]:
    """GU(G) = recommendation proportion - reference proportion.

    Jiang et al. (2024) use historical liked-item proportions as the reference in a
    fine-tuned sequential LRS. This zero-shot audit has no training histories, so the
    pre-registered adaptation uses opportunity in the fixed candidate/catalog pool as the
    reference. Reporting must describe this paradigm gap and include both references when
    persona histories are available.
    """
    groups = set(recommendation_group_counts) | set(reference_group_counts)
    rec_total = sum(recommendation_group_counts.get(group, 0.0) for group in groups)
    ref_total = sum(reference_group_counts.get(group, 0.0) for group in groups)
    if rec_total <= 0 or ref_total <= 0:
        raise ValueError("Group proportions require positive recommendation and reference totals")
    return {
        group: recommendation_group_counts.get(group, 0.0) / rec_total
        - reference_group_counts.get(group, 0.0) / ref_total
        for group in sorted(groups)
    }


def mgu(group_unfairness_values: Mapping[str, float]) -> float:
    if not group_unfairness_values:
        raise ValueError("MGU needs at least one group")
    return float(np.mean(np.abs(list(group_unfairness_values.values()))))


def dgu(group_unfairness_values: Mapping[str, float]) -> float:
    if not group_unfairness_values:
        raise ValueError("DGU needs at least one group")
    values = list(group_unfairness_values.values())
    return float(max(values) - min(values))
