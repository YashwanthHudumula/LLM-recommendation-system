from __future__ import annotations

import pytest

from recllm_fairness.metrics.item_side import (
    average_recommendation_popularity,
    catalog_coverage,
    dgu,
    gini_index,
    group_unfairness,
    hhi,
    long_tail_coverage,
    mgu,
    normalized_hhi,
)


def test_hand_computed_concentration_metrics_include_zero_items() -> None:
    assert gini_index([0, 0, 0, 4]) == pytest.approx(0.75)
    assert hhi([1, 1, 1, 1]) == pytest.approx(0.25)
    assert hhi([0, 0, 0, 4]) == pytest.approx(1.0)
    assert normalized_hhi([1, 1, 1, 1]) == pytest.approx(0.0)
    assert normalized_hhi([0, 0, 0, 4]) == pytest.approx(1.0)


def test_hand_computed_coverage_and_arp() -> None:
    recommendations = ["a", "b", "a"]
    assert catalog_coverage(recommendations, ["a", "b", "c", "d"]) == pytest.approx(0.5)
    assert long_tail_coverage(recommendations, ["b", "c"]) == pytest.approx(0.5)
    assert average_recommendation_popularity(recommendations, {"a": 10, "b": 4}) == pytest.approx(8)


def test_jiang_group_unfairness_mgu_dgu_adaptation() -> None:
    unfairness = group_unfairness({"head": 8, "tail": 2}, {"head": 5, "tail": 5})
    assert unfairness == pytest.approx({"head": 0.3, "tail": -0.3})
    assert mgu(unfairness) == pytest.approx(0.3)
    assert dgu(unfairness) == pytest.approx(0.6)
