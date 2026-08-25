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
    opportunity_adjusted_gini,
    opportunity_adjusted_hhi,
    opportunity_adjusted_normalized_hhi,
    opportunity_selection_rates,
    within_opportunity_coverage,
)


def test_hand_computed_concentration_metrics_include_zero_items() -> None:
    assert gini_index([0, 0, 0, 4]) == pytest.approx(0.75)
    assert hhi([1, 1, 1, 1]) == pytest.approx(0.25)
    assert hhi([0, 0, 0, 4]) == pytest.approx(1.0)
    assert normalized_hhi([1, 1, 1, 1]) == pytest.approx(0.0)
    assert normalized_hhi([0, 0, 0, 4]) == pytest.approx(1.0)
    assert normalized_hhi([0, 0, 0, 0]) == pytest.approx(0.0)


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


def test_hand_computed_within_opportunity_metrics() -> None:
    exposures = [2, 1, 0, 0]
    opportunities = [4, 2, 1, 1]

    assert opportunity_selection_rates(exposures, opportunities) == pytest.approx(
        [0.5, 0.5, 0.0, 0.0]
    )
    assert opportunity_adjusted_gini(exposures, opportunities) == pytest.approx(0.5)
    assert opportunity_adjusted_hhi(exposures, opportunities) == pytest.approx(0.5)
    assert opportunity_adjusted_normalized_hhi(exposures, opportunities) == pytest.approx(1 / 3)
    assert within_opportunity_coverage(exposures, opportunities) == pytest.approx(0.5)


def test_opportunity_adjustment_removes_eligibility_imbalance() -> None:
    exposures = [4, 2, 1, 1]
    opportunities = [8, 4, 2, 2]

    assert gini_index(exposures) > 0
    assert opportunity_adjusted_gini(exposures, opportunities) == pytest.approx(0.0)
    assert opportunity_adjusted_normalized_hhi(exposures, opportunities) == pytest.approx(0.0)


def test_opportunity_metrics_reject_impossible_exposure() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        opportunity_selection_rates([2], [1])
