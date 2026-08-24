from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from recllm_fairness.pipeline.services import (
    bootstrap_item_metric_deltas,
    synthetic_catalog,
)
from recllm_fairness.stats.bootstrap import persona_bootstrap
from recllm_fairness.stats.correlation import classify_scenario, spearman_fairness_scenario
from recllm_fairness.stats.design_simulation import simulate_mixed_model_design
from recllm_fairness.stats.mixed_effects import fit_mixed_effects
from recllm_fairness.stats.multiple_comparison import benjamini_hochberg


def test_persona_bootstrap_resamples_persona_clusters() -> None:
    frame = pd.DataFrame(
        {"persona_id": ["a", "a", "b", "b", "c", "c"], "value": [1, 1, 2, 2, 3, 3]}
    )
    result = persona_bootstrap(
        frame,
        lambda data: float(data["value"].mean()),
        n_resamples=100,
        seed=7,
    )
    assert result.estimate == pytest.approx(2.0)
    assert result.lower <= result.estimate <= result.upper
    assert len(result.replicates) == 100


def test_rq3_scenarios_are_explicit() -> None:
    assert classify_scenario(0.7, 0.01) == "concordant"
    assert classify_scenario(-0.7, 0.01) == "inverse"
    assert classify_scenario(0.7, 0.2) == "independent"
    result = spearman_fairness_scenario(np.arange(8), np.arange(8))
    assert result.scenario == "concordant"


def test_benjamini_hochberg_known_example() -> None:
    rejected, adjusted = benjamini_hochberg([0.01, 0.04, 0.03, 0.20])
    assert rejected.tolist() == [True, False, False, False]
    assert adjusted == pytest.approx([0.04, 0.0533333333, 0.0533333333, 0.2])


def test_design_simulation_reports_power_precision_and_convergence() -> None:
    result = simulate_mixed_model_design(
        simulations=3,
        personas=12,
        phrasings=2,
        repeats=2,
        standardized_effect=0.8,
        seed=9,
    )
    assert 0 <= result.power <= 1
    assert result.mean_ci_width > 0


def test_mixed_effects_wrapper_fits_persona_random_intercepts() -> None:
    rng = np.random.default_rng(4)
    rows = []
    for persona_index in range(20):
        intercept = rng.normal(scale=0.2)
        for level, effect in (("low", 0.0), ("high", 0.5)):
            rows.append(
                {
                    "persona_id": f"p{persona_index}",
                    "trait_level": level,
                    "outcome": intercept + effect + rng.normal(scale=0.05),
                }
            )
    result = fit_mixed_effects(
        pd.DataFrame(rows), outcome="outcome", fixed_effects=("trait_level",)
    )
    assert result.converged
    assert any("trait_level" in term for term in result.params.index)


def test_paired_item_bootstrap_joins_sensitive_traits_to_neutral_rows() -> None:
    catalog = synthetic_catalog(size=12)
    rows = []
    for persona_index in range(3):
        persona = f"p{persona_index}"
        rows.append(
            {
                "model": "model",
                "domain": "movie",
                "trait": "neutral",
                "trait_level": "neutral",
                "phrasing_variant": "direct",
                "persona_id": persona,
                "matched_item_ids": ["movie-0001", "movie-0002"],
            }
        )
        for level, items in (
            ("low", ["movie-0002", "movie-0003"]),
            ("high", ["movie-0003", "movie-0004"]),
        ):
            rows.append(
                {
                    "model": "model",
                    "domain": "movie",
                    "trait": "openness",
                    "trait_level": level,
                    "phrasing_variant": "direct",
                    "persona_id": persona,
                    "matched_item_ids": items,
                }
            )
    result = bootstrap_item_metric_deltas(
        pd.DataFrame(rows),
        catalog,
        k=2,
        n_resamples=20,
        confidence_level=0.95,
        seed=4,
    )
    assert len(result) == 6
    assert set(result["metric"]) == {"gini", "hhi", "arp"}
    assert set(result["trait_level"]) == {"low", "high"}
