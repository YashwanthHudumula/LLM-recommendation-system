from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from recllm_fairness.stats.bootstrap import persona_bootstrap
from recllm_fairness.stats.correlation import classify_scenario, spearman_fairness_scenario
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
