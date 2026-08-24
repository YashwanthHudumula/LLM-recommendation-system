"""Persona-clustered robust alternatives for singular mixed-effects fits."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from recllm_fairness.stats.multiple_comparison import benjamini_hochberg


def fit_cluster_robust_ols(
    data: pd.DataFrame,
    *,
    outcome: str,
    persona_column: str = "persona_id",
    fixed_effects: tuple[str, ...] = ("trait", "trait_level", "phrasing_variant", "model"),
) -> Any:
    """Fit fixed effects with standard errors clustered by independent persona."""
    required = {outcome, persona_column, *fixed_effects}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Cluster-robust data missing columns: {sorted(missing)}")
    clean = data.dropna(subset=list(required)).copy()
    if clean[persona_column].nunique() < 2:
        raise ValueError("Cluster-robust model needs at least two personas")
    formula = outcome + " ~ " + " + ".join(f"C({effect})" for effect in fixed_effects)
    return smf.ols(formula, clean).fit(
        cov_type="cluster",
        cov_kwds={"groups": clean[persona_column], "use_correction": True},
    )


def cluster_robust_effects_tables(
    paired: pd.DataFrame,
    query_item_outcomes: pd.DataFrame,
    *,
    alpha: float,
    standardized_sesoi: float,
) -> pd.DataFrame:
    """Tabulate cluster-robust fits and residual-standardized fixed effects."""
    user = paired.copy()
    for metric in ("jaccard", "serp", "prag"):
        user[f"{metric}_harm"] = 1 - user[metric]
    datasets = [
        (user, ("jaccard_harm", "serp_harm", "prag_harm"), "user_side"),
        (query_item_outcomes, ("query_arp", "head_share", "tail_share"), "item_side"),
    ]
    rows: list[dict[str, object]] = []
    candidate_effects = ("trait", "trait_level", "phrasing_variant", "model")
    for data, outcomes, family in datasets:
        fixed_effects = tuple(
            effect for effect in candidate_effects if data[effect].nunique(dropna=True) > 1
        )
        for outcome in outcomes:
            try:
                result = fit_cluster_robust_ols(
                    data,
                    outcome=outcome,
                    fixed_effects=fixed_effects,
                )
                residual_sd = float(np.std(result.resid, ddof=1))
                if not np.isfinite(residual_sd) or residual_sd <= 0:
                    raise ValueError(f"Cannot standardize {outcome}; residual SD is {residual_sd}")
                intervals = result.conf_int(alpha=alpha)
                for term in result.params.index:
                    standardized = float(result.params[term]) / residual_sd
                    rows.append(
                        {
                            "metric_family": family,
                            "outcome": outcome,
                            "term": term,
                            "coefficient": float(result.params[term]),
                            "standard_error_clustered": float(result.bse[term]),
                            "ci_lower": float(intervals.loc[term, 0]),
                            "ci_upper": float(intervals.loc[term, 1]),
                            "p_value": float(result.pvalues[term]),
                            "residual_sd": residual_sd,
                            "standardized_coefficient": standardized,
                            "meets_standardized_sesoi": abs(standardized) >= standardized_sesoi,
                            "standardized_sesoi": standardized_sesoi,
                            "persona_clusters": int(data["persona_id"].nunique()),
                            "fit_method": "ols_persona_cluster_robust",
                        }
                    )
            except Exception as error:
                rows.append(
                    {
                        "metric_family": family,
                        "outcome": outcome,
                        "term": "__model_failure__",
                        "note": f"{type(error).__name__}: {error}",
                        "fit_method": "ols_persona_cluster_robust",
                    }
                )
    table = pd.DataFrame(rows)
    if "p_value" not in table:
        table["p_value"] = np.nan
    valid = table["p_value"].notna()
    table["p_value_bh"] = np.nan
    table["reject_bh"] = False
    if valid.any():
        rejected, adjusted = benjamini_hochberg(
            table.loc[valid, "p_value"].to_numpy(dtype=float), alpha=alpha
        )
        table.loc[valid, "p_value_bh"] = adjusted
        table.loc[valid, "reject_bh"] = rejected
    return table
