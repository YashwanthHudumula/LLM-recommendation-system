"""Pre-results mixed-model power and precision simulation for the v2 design."""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


@dataclass(frozen=True)
class DesignSimulationResult:
    simulations: int
    personas: int
    phrasings: int
    repeats: int
    standardized_effect: float
    power: float
    mean_ci_width: float
    median_standard_error: float
    convergence_rate: float
    failure_rate: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def simulate_mixed_model_design(
    *,
    simulations: int,
    personas: int = 100,
    phrasings: int = 4,
    repeats: int = 3,
    standardized_effect: float = 0.20,
    random_intercept_sd: float = 0.50,
    residual_sd: float = 1.0,
    alpha: float = 0.05,
    seed: int = 20260731,
) -> DesignSimulationResult:
    """Estimate power for one predeclared trait-pole versus neutral contrast."""
    if min(simulations, personas, phrasings, repeats) < 1:
        raise ValueError("Simulation dimensions must be positive")
    rng = np.random.default_rng(seed)
    significant = 0
    converged = 0
    failures = 0
    widths: list[float] = []
    errors: list[float] = []
    persona_ids = np.repeat(np.arange(personas), 2 * phrasings * repeats)
    condition = np.tile(np.repeat([0, 1], phrasings * repeats), personas)
    phrasing = np.tile(np.tile(np.repeat(np.arange(phrasings), repeats), 2), personas)
    for _ in range(simulations):
        intercepts = rng.normal(0, random_intercept_sd, personas)
        outcome = (
            intercepts[persona_ids]
            + standardized_effect * residual_sd * condition
            + rng.normal(0, residual_sd, len(persona_ids))
        )
        frame = pd.DataFrame(
            {
                "outcome": outcome,
                "condition": condition,
                "phrasing": phrasing,
                "persona": persona_ids,
            }
        )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = smf.mixedlm(
                    "outcome ~ condition + C(phrasing)", frame, groups=frame["persona"]
                ).fit(reml=False, method="powell", disp=False)
            if bool(fit.converged):
                converged += 1
            estimate = float(fit.params["condition"])
            standard_error = float(fit.bse["condition"])
            p_value = float(fit.pvalues["condition"])
            if np.isfinite(estimate) and np.isfinite(standard_error) and np.isfinite(p_value):
                errors.append(standard_error)
                widths.append(2 * 1.959963984540054 * standard_error)
                significant += int(p_value < alpha)
            else:
                failures += 1
        except Exception:
            failures += 1
    valid = simulations - failures
    if valid == 0:
        raise RuntimeError("All mixed-model simulations failed")
    return DesignSimulationResult(
        simulations,
        personas,
        phrasings,
        repeats,
        standardized_effect,
        significant / valid,
        float(np.mean(widths)),
        float(np.median(errors)),
        converged / simulations,
        failures / simulations,
    )
