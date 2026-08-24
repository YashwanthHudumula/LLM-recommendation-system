"""The core catalog-aggregation layer: queries -> per-condition item exposures."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

DEFAULT_CONDITION_COLUMNS = [
    "model",
    "domain",
    "trait",
    "trait_level",
    "phrasing_variant",
]


def aggregate_exposure(
    queries: pd.DataFrame,
    *,
    k: int,
    condition_columns: Sequence[str] = DEFAULT_CONDITION_COLUMNS,
    rank_discount: bool = False,
) -> pd.DataFrame:
    """Explode matched lists into reviewable per-item exposure rows.

    Each query contributes at most K matched catalog items. Uniform exposure is the primary
    pre-registered view; logarithmic rank-discounted exposure is a sensitivity analysis.
    """
    if k < 1:
        raise ValueError("k must be positive")
    required = {"query_id", "persona_id", "matched_item_ids", *condition_columns}
    missing = required - set(queries.columns)
    if missing:
        raise ValueError(f"Query table missing aggregation columns: {sorted(missing)}")
    records: list[dict[str, object]] = []
    for row in queries.to_dict(orient="records"):
        item_ids = list(row["matched_item_ids"])[:k]
        for rank, item_id in enumerate(item_ids, 1):
            record = {column: row[column] for column in condition_columns}
            record.update(
                query_id=row["query_id"],
                persona_id=row["persona_id"],
                item_id=item_id,
                rank=rank,
                exposure_weight=(1 / np.log2(rank + 1)) if rank_discount else 1.0,
            )
            records.append(record)
    return pd.DataFrame(records)


def exposure_counts(
    exposures: pd.DataFrame,
    *,
    condition_columns: Sequence[str] = DEFAULT_CONDITION_COLUMNS,
) -> pd.DataFrame:
    """Pool exploded rows into item counts/weights per experimental condition."""
    if exposures.empty:
        return pd.DataFrame(columns=[*condition_columns, "item_id", "exposure_count", "exposure"])
    return (
        exposures.groupby([*condition_columns, "item_id"], dropna=False)
        .agg(exposure_count=("item_id", "size"), exposure=("exposure_weight", "sum"))
        .reset_index()
    )
