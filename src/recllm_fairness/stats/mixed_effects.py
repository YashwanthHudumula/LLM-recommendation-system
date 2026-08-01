"""Statsmodels mixed-effects wrapper with persona random intercepts."""

from __future__ import annotations

from typing import Any

import pandas as pd
import statsmodels.formula.api as smf


def fit_mixed_effects(
    data: pd.DataFrame,
    *,
    outcome: str,
    persona_column: str = "persona_id",
    fixed_effects: tuple[str, ...] = ("trait", "trait_level", "phrasing_variant", "model"),
    reml: bool = False,
) -> Any:
    """Fit outcome ~ categorical fixed effects with a persona random intercept."""
    required = {outcome, persona_column, *fixed_effects}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Mixed-effects data missing columns: {sorted(missing)}")
    clean = data.dropna(subset=list(required)).copy()
    if clean[persona_column].nunique() < 2:
        raise ValueError("Mixed-effects model needs at least two personas")
    formula = outcome + " ~ " + " + ".join(f"C({effect})" for effect in fixed_effects)
    return smf.mixedlm(formula, clean, groups=clean[persona_column]).fit(
        reml=reml, method="lbfgs"
    )

