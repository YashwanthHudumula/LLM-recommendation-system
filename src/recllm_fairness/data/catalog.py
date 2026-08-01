"""Domain-independent item schema and popularity tier assignment."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class Item(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    domain: Literal["movie", "music"]
    title: str = Field(min_length=1)
    genres: list[str] = Field(default_factory=list)
    provider_or_studio: str | None = None
    popularity_rank: int = Field(ge=1)
    popularity_tier: Literal["head", "mid", "tail"]
    interaction_count: int | None = Field(default=None, ge=1)
    release_year: int | None = Field(default=None, ge=1800, le=2200)


def assign_popularity_tiers(
    frame: pd.DataFrame,
    *,
    count_column: str = "interaction_count",
    id_column: str = "item_id",
    head_quantile: float = 1 / 3,
    mid_quantile: float = 2 / 3,
) -> pd.DataFrame:
    """Rank by interactions and split the ranked *items* into configured quantiles.

    Ties are resolved by item ID so identical inputs produce identical catalogs.
    """
    if frame.empty:
        raise ValueError("Cannot tier an empty catalog")
    if not 0 < head_quantile < mid_quantile < 1:
        raise ValueError("Tier quantiles must satisfy 0 < head < mid < 1")
    if frame[id_column].duplicated().any():
        raise ValueError("Catalog item IDs must be unique before tier assignment")
    ranked = frame.copy()
    ranked[id_column] = ranked[id_column].astype(str)
    ranked = ranked.sort_values(
        [count_column, id_column], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)
    ranked["popularity_rank"] = range(1, len(ranked) + 1)
    positions = ranked["popularity_rank"] / len(ranked)
    ranked["popularity_tier"] = "tail"
    ranked.loc[positions <= mid_quantile, "popularity_tier"] = "mid"
    ranked.loc[positions <= head_quantile, "popularity_tier"] = "head"
    return ranked


def items_to_frame(items: Iterable[Item]) -> pd.DataFrame:
    """Convert validated items to a DataFrame without object identity surprises."""
    return pd.DataFrame([item.model_dump() for item in items])
