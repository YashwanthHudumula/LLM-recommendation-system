"""MovieLens 1M and 25M loaders targeting the unified Item schema."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, cast

import pandas as pd

from recllm_fairness.data.catalog import Item, assign_popularity_tiers
from recllm_fairness.data.provenance import verify_checksum

__all__ = ["MOVIELENS_MD5", "load_movielens", "verify_checksum"]

MOVIELENS_MD5 = {
    "1m": "c4d9eecfca2ab87c1945afe126590906",
    "25m": "6b51fb2759a8657d3bfcbfc42b592ada",
}
_YEAR = re.compile(r"\s*\((\d{4})\)\s*$")


def _title_and_year(value: str) -> tuple[str, int | None]:
    match = _YEAR.search(value)
    if not match:
        return value.strip(), None
    return value[: match.start()].strip(), int(match.group(1))


def load_movielens(
    root: str | Path,
    version: str,
    *,
    head_quantile: float = 1 / 3,
    mid_quantile: float = 2 / 3,
) -> list[Item]:
    """Load an extracted `ml-1m` or `ml-25m` directory."""
    source = Path(root)
    if version == "1m":
        movies = pd.read_csv(
            source / "movies.dat",
            sep="::",
            engine="python",
            names=["item_id", "raw_title", "genres"],
            encoding="latin-1",
        )
        ratings = pd.read_csv(
            source / "ratings.dat",
            sep="::",
            engine="python",
            usecols=[1],
            names=["user_id", "item_id", "rating", "timestamp"],
            encoding="latin-1",
        )
    elif version == "25m":
        movies = pd.read_csv(source / "movies.csv").rename(
            columns={"movieId": "item_id", "title": "raw_title"}
        )
        ratings = pd.read_csv(source / "ratings.csv", usecols=["movieId"]).rename(
            columns={"movieId": "item_id"}
        )
    else:
        raise ValueError("MovieLens version must be '1m' or '25m'")

    counts = ratings.groupby("item_id", sort=False).size().rename("interaction_count")
    catalog = movies.join(counts, on="item_id").dropna(subset=["interaction_count"]).copy()
    catalog["interaction_count"] = catalog["interaction_count"].astype(int)
    parsed = catalog["raw_title"].astype(str).map(_title_and_year)
    catalog["title"] = parsed.map(lambda pair: pair[0])
    catalog["release_year"] = parsed.map(lambda pair: pair[1])
    catalog["item_id"] = catalog["item_id"].astype(str)
    catalog = assign_popularity_tiers(
        catalog,
        head_quantile=head_quantile,
        mid_quantile=mid_quantile,
    )
    return [
        Item(
            item_id=str(row["item_id"]),
            domain="movie",
            title=str(row["title"]),
            genres=[]
            if row["genres"] == "(no genres listed)"
            else str(row["genres"]).split("|"),
            provider_or_studio=None,
            popularity_rank=int(row["popularity_rank"]),
            popularity_tier=cast(
                Literal["head", "mid", "tail"], str(row["popularity_tier"])
            ),
            interaction_count=int(row["interaction_count"]),
            release_year=None if pd.isna(row["release_year"]) else int(row["release_year"]),
        )
        for row in catalog.to_dict(orient="records")
    ]
