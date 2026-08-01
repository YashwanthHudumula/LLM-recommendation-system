from __future__ import annotations

import math

import pandas as pd
import pytest

from recllm_fairness.metrics.aggregate import aggregate_exposure, exposure_counts
from recllm_fairness.metrics.relevance import ndcg_at_k, precision_at_k


def test_aggregate_exposure_preserves_condition_and_rank() -> None:
    queries = pd.DataFrame(
        [
            {
                "query_id": "q1",
                "persona_id": "p1",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "matched_item_ids": ["a", "b", "c"],
            },
            {
                "query_id": "q2",
                "persona_id": "p2",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "matched_item_ids": ["a", "c"],
            },
        ]
    )
    exploded = aggregate_exposure(queries, k=2)
    assert exploded["item_id"].tolist() == ["a", "b", "a", "c"]
    assert exploded["rank"].tolist() == [1, 2, 1, 2]
    counts = exposure_counts(exploded)
    assert counts.set_index("item_id").loc["a", "exposure_count"] == 2


def test_relevance_metrics_have_hand_computed_values() -> None:
    assert precision_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(2 / 3)
    expected = (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(expected)
