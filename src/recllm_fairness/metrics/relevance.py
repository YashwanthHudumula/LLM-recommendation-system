"""Utility controls against independently constructed relevant-item sets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def precision_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    return len(set(recommended[:k]) & relevant) / k


def ndcg_at_k(
    recommended: Sequence[str],
    relevance: Mapping[str, float] | set[str],
    k: int,
) -> float:
    if k < 1:
        raise ValueError("k must be positive")
    scores = (
        {item: 1.0 for item in relevance}
        if isinstance(relevance, set)
        else {item: float(score) for item, score in relevance.items()}
    )
    gains = [scores.get(item, 0.0) for item in recommended[:k]]
    dcg = sum((2**gain - 1) / np.log2(rank + 1) for rank, gain in enumerate(gains, 1))
    ideal = sorted(scores.values(), reverse=True)[:k]
    idcg = sum((2**gain - 1) / np.log2(rank + 1) for rank, gain in enumerate(ideal, 1))
    return 0.0 if idcg == 0 else float(dcg / idcg)

