"""Deterministic construction of independent v2 personas from full datasets."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from recllm_fairness.data.candidate_pool import CandidatePool, build_candidate_pool
from recllm_fairness.data.catalog import Item
from recllm_fairness.data.lastfm import stable_artist_id

Domain = Literal["movie", "music"]


@dataclass(frozen=True)
class PopulationProfile:
    profile_id: str
    domain: Domain
    stated_preferences: str
    construction_item_ids: list[str]
    relevant_item_ids: list[str]
    stratum: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_score(seed: int, namespace: str, value: object) -> int:
    payload = f"{seed}|{namespace}|{value}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _entropy(values: pd.Series) -> float:
    counts = values.value_counts().to_numpy(dtype=float)
    probabilities = counts / counts.sum()
    return float(-(probabilities * np.log(probabilities)).sum())


def _natural_join(values: Sequence[object]) -> str:
    words = [str(value) for value in values]
    if len(words) < 2:
        return "" if not words else words[0]
    if len(words) == 2:
        return " and ".join(words)
    return f"{', '.join(words[:-1])}, and {words[-1]}"


def _quantile_labels(values: pd.Series) -> tuple[pd.Series, list[float]]:
    boundaries = [float(values.quantile(1 / 3)), float(values.quantile(2 / 3))]
    labels = pd.cut(
        values,
        bins=[-math.inf, boundaries[0], boundaries[1], math.inf],
        labels=["low", "mid", "high"],
        include_lowest=True,
    ).astype("string")
    return labels, boundaries


def _balanced_sample(frame: pd.DataFrame, *, seed: int, count: int) -> pd.DataFrame:
    work = frame.copy()
    work["_score"] = [_stable_score(seed, "sample", value) for value in work["raw_user_id"]]
    work = work.sort_values(["stratum", "_score"], kind="mergesort")
    groups = {key: group.copy() for key, group in work.groupby("stratum", sort=True)}
    chosen: list[pd.DataFrame] = []
    while sum(len(part) for part in chosen) < count:
        progressed = False
        for key in sorted(groups, key=str):
            if groups[key].empty:
                continue
            chosen.append(groups[key].iloc[:1])
            groups[key] = groups[key].iloc[1:]
            progressed = True
            if sum(len(part) for part in chosen) == count:
                break
        if not progressed:
            raise ValueError(f"Only {sum(len(part) for part in chosen)} eligible profiles")
    return pd.concat(chosen, ignore_index=True).drop(columns="_score")


def _split_ids(
    ids: list[str], *, seed: int, user_id: object, fraction: float
) -> tuple[list[str], list[str]]:
    ordered = sorted(ids, key=lambda item: _stable_score(seed, f"split|{user_id}", item))
    cut = max(1, min(len(ordered) - 1, int(len(ordered) * fraction)))
    return ordered[:cut], ordered[cut:]


def construct_movie_population(
    root: str | Path,
    *,
    seed: int = 20260731,
    count: int = 100,
    positive_threshold: float = 4.0,
    minimum_positive: int = 60,
    construction_fraction: float = 0.5,
) -> tuple[list[PopulationProfile], dict[str, Any]]:
    source = Path(root)
    ratings = pd.read_csv(
        source / "ratings.csv",
        usecols=["userId", "movieId", "rating"],
        dtype={"userId": "int32", "movieId": "int32", "rating": "float32"},
    )
    movies = pd.read_csv(source / "movies.csv", dtype={"movieId": "int32"})
    positive = ratings.loc[ratings["rating"] >= positive_threshold].copy()
    popularity = ratings.groupby("movieId").size().rank(ascending=False, method="average")
    positive["popularity_percentile"] = positive["movieId"].map(popularity) / len(popularity)
    exploded = positive.merge(movies, on="movieId", how="left")
    exploded["genre"] = exploded["genres"].str.split("|")
    exploded = exploded.explode("genre")
    base = positive.groupby("userId").agg(
        activity=("movieId", "nunique"), popularity_tendency=("popularity_percentile", "mean")
    )
    diversity = exploded.groupby("userId")["genre"].apply(_entropy).rename("diversity")
    eligible = base.join(diversity).loc[lambda x: x["activity"] >= minimum_positive].copy()
    eligible["raw_user_id"] = eligible.index.astype(str)
    boundaries: dict[str, list[float]] = {}
    for dimension in ["activity", "popularity_tendency", "diversity"]:
        eligible[dimension + "_band"], boundaries[dimension] = _quantile_labels(eligible[dimension])
    eligible["stratum"] = eligible[
        ["activity_band", "popularity_tendency_band", "diversity_band"]
    ].agg("/".join, axis=1)
    selected = _balanced_sample(eligible.reset_index(drop=True), seed=seed, count=count)
    title_features = movies.set_index("movieId")
    profiles: list[PopulationProfile] = []
    for ordinal, (_, row) in enumerate(selected.iterrows()):
        user_id = int(row["raw_user_id"])
        user_ids = (
            positive.loc[positive["userId"] == user_id, "movieId"].astype(str).unique().tolist()
        )
        construction, evaluation = _split_ids(
            user_ids, seed=seed, user_id=user_id, fraction=construction_fraction
        )
        construction_movies = title_features.loc[[int(item) for item in construction]]
        genres = (
            construction_movies["genres"]
            .str.split("|")
            .explode()
            .value_counts()
            .head(3)
            .index.tolist()
        )
        years = construction_movies["title"].str.extract(r"\((\d{4})\)\s*$")[0].dropna().astype(int)
        decades = years.floordiv(10).mul(10).value_counts().head(2).index.tolist()
        era = (
            _natural_join([f"the {decade}s" for decade in decades])
            if decades
            else "a range of eras"
        )
        preference = (
            f"I enjoy films in genres such as {_natural_join(genres)}, "
            f"especially titles from {era}."
        )
        profiles.append(
            PopulationProfile(
                f"movie-v2-{ordinal + 1:03d}",
                "movie",
                preference,
                construction,
                evaluation,
                str(row["stratum"]),
            )
        )
    diagnostics = {
        "eligible_users": len(eligible),
        "threshold": positive_threshold,
        "minimum_positive": minimum_positive,
        "construction_fraction": construction_fraction,
        "strata_boundaries": boundaries,
    }
    return profiles, diagnostics


def construct_music_population(
    root: str | Path,
    *,
    seed: int = 20260731,
    count: int = 100,
    minimum_distinct_artists: int = 60,
    construction_fraction: float = 0.5,
) -> tuple[list[PopulationProfile], dict[str, Any]]:
    path = Path(root) / "usersha1-artmbid-artname-plays.tsv"
    events = pd.read_csv(
        path,
        sep="\t",
        names=["raw_user_id", "mbid", "artist", "plays"],
        dtype={"raw_user_id": "string", "mbid": "string", "artist": "string", "plays": "Int64"},
        on_bad_lines="skip",
    ).dropna(subset=["raw_user_id", "artist", "plays"])
    events = events.loc[events["plays"] > 0].copy()
    events["item_id"] = [
        stable_artist_id(mbid, name)
        for mbid, name in zip(events["mbid"], events["artist"], strict=True)
    ]
    artist_popularity = (
        events.groupby("item_id")["plays"].sum().rank(ascending=False, method="average")
    )
    events["popularity_percentile"] = events["item_id"].map(artist_popularity) / len(
        artist_popularity
    )
    totals = events.groupby("raw_user_id")["plays"].transform("sum")
    events["share"] = events["plays"] / totals
    events["entropy_part"] = -events["share"] * np.log(events["share"])
    eligible = events.groupby("raw_user_id").agg(
        activity=("item_id", "nunique"),
        popularity_tendency=("popularity_percentile", "mean"),
        diversity=("entropy_part", "sum"),
    )
    eligible = eligible.loc[lambda x: x["activity"] >= minimum_distinct_artists].reset_index()
    boundaries: dict[str, list[float]] = {}
    for dimension in ["activity", "popularity_tendency", "diversity"]:
        eligible[dimension + "_band"], boundaries[dimension] = _quantile_labels(eligible[dimension])
    eligible["stratum"] = eligible[
        ["activity_band", "popularity_tendency_band", "diversity_band"]
    ].agg("/".join, axis=1)
    selected = _balanced_sample(eligible, seed=seed, count=count)
    profiles: list[PopulationProfile] = []
    for ordinal, (_, row) in enumerate(selected.iterrows()):
        user_id = str(row["raw_user_id"])
        history = events.loc[events["raw_user_id"] == user_id].drop_duplicates("item_id").copy()
        ids = history["item_id"].astype(str).tolist()
        construction, evaluation = _split_ids(
            ids, seed=seed, user_id=user_id, fraction=construction_fraction
        )
        seeds = (
            history.loc[history["item_id"].isin(construction)]
            .sort_values(["plays", "artist"], ascending=[False, True])
            .head(5)["artist"]
            .astype(str)
            .tolist()
        )
        punctuation = "" if seeds[-1].endswith((".", "?", "!")) else "."
        preference = f"I often listen to artists such as {_natural_join(seeds)}{punctuation}"
        profiles.append(
            PopulationProfile(
                f"music-v2-{ordinal + 1:03d}",
                "music",
                preference,
                construction,
                evaluation,
                str(row["stratum"]),
            )
        )
    diagnostics = {
        "eligible_users": len(eligible),
        "minimum_distinct_artists": minimum_distinct_artists,
        "construction_fraction": construction_fraction,
        "strata_boundaries": boundaries,
    }
    return profiles, diagnostics


def audit_population(
    profiles: list[PopulationProfile], *, expected_count: int = 100, minimum_relevant: int = 30
) -> dict[str, Any]:
    ids = [profile.profile_id for profile in profiles]
    leakage = [
        profile.profile_id
        for profile in profiles
        if set(profile.construction_item_ids) & set(profile.relevant_item_ids)
    ]
    insufficient = [
        profile.profile_id
        for profile in profiles
        if len(profile.relevant_item_ids) < minimum_relevant
    ]
    duplicate_records = len(
        {
            (
                profile.domain,
                profile.stated_preferences,
                tuple(profile.construction_item_ids),
                tuple(profile.relevant_item_ids),
            )
            for profile in profiles
        }
    ) != len(profiles)
    passed = (
        len(profiles) == expected_count
        and len(set(ids)) == expected_count
        and not leakage
        and not insufficient
        and not duplicate_records
    )
    return {
        "passed": passed,
        "profile_count": len(profiles),
        "unique_profile_ids": len(set(ids)),
        "leakage_profile_ids": leakage,
        "insufficient_relevant_profile_ids": insufficient,
        "duplicate_profile_records": duplicate_records,
    }


def build_population_candidate_pools(
    profiles: list[PopulationProfile],
    catalog: list[Item],
    *,
    seed: int = 20260731,
    size: int = 120,
    minimum_relevant: int = 30,
) -> dict[str, CandidatePool]:
    """Build a profile-specific, relevance-aware 50/25/25 candidate pool."""
    catalog_ids = {item.item_id for item in catalog}
    pools: dict[str, CandidatePool] = {}
    for profile in profiles:
        missing = set(profile.relevant_item_ids) - catalog_ids
        if missing:
            raise ValueError(
                f"{profile.profile_id} has {len(missing)} relevant IDs outside the catalog"
            )
        profile_seed = _stable_score(seed, "candidate-pool", profile.profile_id)
        pools[profile.profile_id] = build_candidate_pool(
            catalog,
            size=size,
            head_fraction=0.5,
            mid_fraction=0.25,
            tail_fraction=0.25,
            seed=profile_seed,
            required_item_ids=profile.relevant_item_ids,
            minimum_required=minimum_relevant,
            shuffle_items=True,
        )
    return pools


def audit_candidate_pools(
    profiles: list[PopulationProfile],
    pools: dict[str, CandidatePool],
    catalog: list[Item],
    *,
    expected_size: int = 120,
    minimum_relevant: int = 30,
) -> dict[str, Any]:
    """Audit grounding, tier allocation, relevance opportunity, and uniqueness."""
    catalog_ids = {item.item_id for item in catalog}
    profile_by_id = {profile.profile_id: profile for profile in profiles}
    failures: dict[str, list[str]] = {
        "missing_pool": [],
        "wrong_size": [],
        "duplicate_items": [],
        "off_catalog_items": [],
        "wrong_tier_allocation": [],
        "insufficient_relevant_opportunity": [],
    }
    expected_tiers = {"head": 60, "mid": 30, "tail": 30}
    for profile_id, profile in profile_by_id.items():
        pool = pools.get(profile_id)
        if pool is None:
            failures["missing_pool"].append(profile_id)
            continue
        ids = [item.item_id for item in pool.items]
        if len(ids) != expected_size:
            failures["wrong_size"].append(profile_id)
        if len(set(ids)) != len(ids):
            failures["duplicate_items"].append(profile_id)
        if not set(ids) <= catalog_ids:
            failures["off_catalog_items"].append(profile_id)
        tiers = {
            tier: sum(item.popularity_tier == tier for item in pool.items)
            for tier in expected_tiers
        }
        if tiers != expected_tiers:
            failures["wrong_tier_allocation"].append(profile_id)
        if len(set(ids) & set(profile.relevant_item_ids)) < minimum_relevant:
            failures["insufficient_relevant_opportunity"].append(profile_id)
    passed = len(pools) == len(profiles) and not any(failures.values())
    return {
        "passed": passed,
        "profile_count": len(profiles),
        "pool_count": len(pools),
        "expected_size": expected_size,
        "expected_tier_allocation": expected_tiers,
        "minimum_relevant_opportunity": minimum_relevant,
        "failures": failures,
    }
