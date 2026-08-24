"""LastFM-1K and LastFM-360K artist-level catalog loaders."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal, cast

import pandas as pd

from recllm_fairness.data.catalog import Item, assign_popularity_tiers
from recllm_fairness.data.provenance import verify_checksum

__all__ = ["LASTFM_ARCHIVE_MD5", "load_lastfm", "stable_artist_id", "verify_checksum"]

LASTFM_ARCHIVE_MD5 = {
    "1k": "a79a6808f54f73354789a9fb02cb1e41",
    "360k": "635e6ed3fc873aa4ba33aba0ebce02b1",
}


def stable_artist_id(mbid: object, name: str) -> str:
    if isinstance(mbid, str) and mbid.strip():
        return mbid.strip()
    normalized = " ".join(name.casefold().split())
    return "name:" + hashlib.sha1(normalized.encode()).hexdigest()


def load_lastfm(
    root: str | Path,
    version: str,
    *,
    head_quantile: float = 1 / 3,
    mid_quantile: float = 2 / 3,
) -> list[Item]:
    """Load an extracted release and aggregate it to artist-level items."""
    source = Path(root)
    if version == "1k":
        path = source / "userid-timestamp-artid-artname-traid-traname.tsv"
        events = pd.read_csv(
            path,
            sep="\t",
            names=["user_id", "timestamp", "artist_mbid", "artist_name", "track_mbid", "track"],
            usecols=[0, 2, 3],
            dtype=str,
            on_bad_lines="skip",
        )
        events = events.dropna(subset=["artist_name"])
        events["plays"] = 1
    elif version == "360k":
        path = source / "usersha1-artmbid-artname-plays.tsv"
        events = pd.read_csv(
            path,
            sep="\t",
            names=["user_id", "artist_mbid", "artist_name", "plays"],
            dtype={"user_id": str, "artist_mbid": str, "artist_name": str, "plays": "Int64"},
            on_bad_lines="skip",
        ).dropna(subset=["artist_name", "plays"])
    else:
        raise ValueError("LastFM version must be '1k' or '360k'")

    events["item_id"] = [
        stable_artist_id(mbid, name)
        for mbid, name in zip(events["artist_mbid"], events["artist_name"], strict=True)
    ]
    # MBID-bearing rows are authoritative; name is selected deterministically for dirty aliases.
    aggregated = (
        events.groupby("item_id", as_index=False)
        .agg(title=("artist_name", "first"), interaction_count=("plays", "sum"))
        .sort_values("item_id", kind="mergesort")
    )
    catalog = assign_popularity_tiers(
        aggregated,
        head_quantile=head_quantile,
        mid_quantile=mid_quantile,
    )
    return [
        Item(
            item_id=str(row["item_id"]),
            domain="music",
            title=str(row["title"]),
            genres=[],
            provider_or_studio=None,
            popularity_rank=int(row["popularity_rank"]),
            popularity_tier=cast(Literal["head", "mid", "tail"], str(row["popularity_tier"])),
            interaction_count=int(row["interaction_count"]),
            release_year=None,
        )
        for row in catalog.to_dict(orient="records")
    ]
