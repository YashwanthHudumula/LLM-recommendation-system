"""Dataset-internal construction of fixed relevance labels.

No model output is read here. Movie labels use declared genre logic plus a reliability
filter; music labels use binary user-artist co-listening vectors.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from recllm_fairness.data.catalog import Item
from recllm_fairness.data.lastfm import stable_artist_id
from recllm_fairness.personas.traits import TRAIT_CODES, marker_text


def load_design(path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("Persona/relevance design must be a YAML mapping")
    return value


def _genre_match(genres: set[str], rule: Mapping[str, object]) -> bool:
    raw_all = rule.get("all_of", [])
    raw_any = rule.get("any_of", [])
    if not isinstance(raw_all, Sequence) or isinstance(raw_all, str):
        raise TypeError("genre_rule.all_of must be a sequence")
    if not isinstance(raw_any, Sequence) or isinstance(raw_any, str):
        raise TypeError("genre_rule.any_of must be a sequence")
    all_of = {str(value) for value in raw_all}
    any_of = {str(value) for value in raw_any}
    return all_of.issubset(genres) and (not any_of or bool(any_of & genres))


def build_movie_labels(
    catalog: Sequence[Item],
    preferences: Sequence[Mapping[str, object]],
    *,
    min_ratings: int,
    dataset_version: str,
    design_version: str,
) -> dict[str, Any]:
    """Construct complete genre-defined movie relevance sets without popularity truncation."""
    if min_ratings < 1:
        raise ValueError("min_ratings must be positive")
    entries: list[dict[str, object]] = []
    for preference in preferences:
        raw_rule = preference.get("genre_rule")
        if not isinstance(raw_rule, Mapping):
            raise TypeError("Every movie preference needs a genre_rule mapping")
        relevant = sorted(
            (
                item
                for item in catalog
                if (item.interaction_count or 0) >= min_ratings
                and _genre_match(set(item.genres), raw_rule)
            ),
            key=lambda item: int(item.item_id),
        )
        entries.append(
            {
                "id": str(preference["id"]),
                "text": str(preference["text"]),
                "genre_rule": dict(raw_rule),
                "min_ratings": min_ratings,
                "relevant_count": len(relevant),
                "relevant_item_ids": [item.item_id for item in relevant],
            }
        )
    return {
        "schema_version": 1,
        "design_version": design_version,
        "domain": "movie",
        "dataset": {"name": "MovieLens", "version": dataset_version},
        "method": "genre_rule_with_minimum_rating_count",
        "parameters": {"min_ratings": min_ratings, "truncate": False},
        "preferences": entries,
    }


def read_lastfm_listener_pairs(root: str | Path, version: str) -> pd.DataFrame:
    """Read one binary row per user/artist while retaining a deterministic display name."""
    source = Path(root)
    if version == "1k":
        frame = pd.read_csv(
            source / "userid-timestamp-artid-artname-traid-traname.tsv",
            sep="\t",
            names=["user_id", "timestamp", "artist_mbid", "artist_name", "track_mbid", "track"],
            usecols=[0, 2, 3],
            dtype=str,
            on_bad_lines="skip",
        )
    elif version == "360k":
        frame = pd.read_csv(
            source / "usersha1-artmbid-artname-plays.tsv",
            sep="\t",
            names=["user_id", "artist_mbid", "artist_name", "plays"],
            usecols=[0, 1, 2],
            dtype=str,
            on_bad_lines="skip",
        )
    else:
        raise ValueError("LastFM version must be '1k' or '360k'")
    frame = frame.dropna(subset=["user_id", "artist_name"])
    frame["item_id"] = [
        stable_artist_id(mbid, name)
        for mbid, name in zip(frame["artist_mbid"], frame["artist_name"], strict=True)
    ]
    frame["normalized_artist_name"] = (
        frame["artist_name"].str.casefold().str.split().str.join(" ")
    )
    return frame[
        ["user_id", "item_id", "artist_name", "normalized_artist_name"]
    ].drop_duplicates(["user_id", "item_id"])


def build_music_labels(
    listener_pairs: pd.DataFrame,
    preferences: Sequence[Mapping[str, object]],
    *,
    min_seed_listeners: int,
    min_candidate_listeners: int,
    cosine_threshold: float,
    acceptable_size: tuple[int, int],
    dataset_version: str,
    design_version: str,
) -> dict[str, Any]:
    """Construct relevance via cosine similarity to each seed-set union listener vector."""
    required = {"user_id", "item_id", "artist_name", "normalized_artist_name"}
    missing = required - set(listener_pairs.columns)
    if missing:
        raise ValueError(f"Listener pairs missing columns: {sorted(missing)}")
    if min_seed_listeners < 1 or min_candidate_listeners < 1:
        raise ValueError("Listener thresholds must be positive")
    if not 0 < cosine_threshold <= 1:
        raise ValueError("cosine_threshold must be in (0, 1]")
    lower, upper = acceptable_size
    pairs = listener_pairs.drop_duplicates(["user_id", "item_id"]).copy()
    listener_counts = pairs.groupby("item_id", sort=False).size()
    title_by_id = pairs.groupby("item_id", sort=False)["artist_name"].first()
    entries: list[dict[str, object]] = []
    for preference in preferences:
        raw_seeds = preference.get("seed_artists")
        if not isinstance(raw_seeds, Sequence) or isinstance(raw_seeds, str):
            raise TypeError("Every music preference needs a seed_artists sequence")
        seed_audit: list[dict[str, object]] = []
        union_listeners: set[str] = set()
        seed_item_ids: set[str] = set()
        for raw_seed in raw_seeds:
            seed = str(raw_seed)
            normalized = " ".join(seed.casefold().split())
            matches = pairs.loc[pairs["normalized_artist_name"] == normalized]
            if matches.empty:
                raise ValueError(f"Seed artist not found exactly in LastFM: {seed}")
            listeners = set(matches["user_id"].astype(str))
            matched_ids = sorted(set(matches["item_id"].astype(str)))
            if len(listeners) < min_seed_listeners:
                raise ValueError(
                    f"Seed artist {seed} has {len(listeners)} listeners; "
                    f"minimum is {min_seed_listeners}"
                )
            union_listeners.update(listeners)
            seed_item_ids.update(matched_ids)
            seed_audit.append(
                {
                    "artist": seed,
                    "listener_count": len(listeners),
                    "matched_item_ids": matched_ids,
                }
            )
        union_size = len(union_listeners)
        intersections = (
            pairs.loc[pairs["user_id"].isin(union_listeners)]
            .groupby("item_id", sort=False)
            .size()
        )
        candidates = listener_counts.loc[listener_counts >= min_candidate_listeners]
        similarities = {
            str(item_id): float(intersections.get(item_id, 0))
            / math.sqrt(float(count) * union_size)
            for item_id, count in candidates.items()
        }
        relevant_ids = sorted(
            item_id for item_id, score in similarities.items() if score >= cosine_threshold
        )
        relevant_artists = [str(title_by_id.loc[item_id]) for item_id in relevant_ids]
        entries.append(
            {
                "id": str(preference["id"]),
                "text": str(preference["text"]),
                "seed_artists": [str(seed) for seed in raw_seeds],
                "seed_item_ids": sorted(seed_item_ids),
                "seed_listener_audit": seed_audit,
                "seed_union_listener_count": union_size,
                "relevant_count": len(relevant_ids),
                "within_acceptable_size": lower <= len(relevant_ids) <= upper,
                "relevant_item_ids": relevant_ids,
                "relevant_artist_names": relevant_artists,
            }
        )
    return {
        "schema_version": 1,
        "design_version": design_version,
        "domain": "music",
        "dataset": {"name": "LastFM", "version": dataset_version},
        "method": "binary_listener_cosine_to_seed_union",
        "parameters": {
            "min_seed_listeners": min_seed_listeners,
            "min_candidate_listeners": min_candidate_listeners,
            "cosine_threshold": cosine_threshold,
            "acceptable_relevant_set_size": [lower, upper],
        },
        "all_sets_within_acceptable_size": all(
            bool(entry["within_acceptable_size"]) for entry in entries
        ),
        "preferences": entries,
    }


def write_label_file(path: str | Path, labels: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(labels, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_audit_bundle(
    design: Mapping[str, object],
    movie_labels: Mapping[str, object],
    music_labels: Mapping[str, object],
) -> dict[str, object]:
    """Combine wording, criteria, and labels into one reviewable versioned artifact."""
    framings: list[dict[str, object]] = []
    for (trait, level), code in TRAIT_CODES.items():
        framings.append(
            {
                "code": code,
                "trait": trait,
                "level": level,
                "sentence": marker_text(trait, level),
            }
        )
    framings.append(
        {
            "code": "NEU",
            "trait": "neutral",
            "level": "neutral",
            "sentence": "",
        }
    )
    return {
        "schema_version": 1,
        "design_version": design["design_version"],
        "status": design["status"],
        "trait_framings": framings,
        "design": dict(design),
        "relevance_labels": {
            "movie": dict(movie_labels),
            "music": dict(music_labels),
        },
    }


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_label_preferences(path: str | Path) -> list[dict[str, object]]:
    """Load the structured preference input consumed by persona generation."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = value.get("preferences")
    if not isinstance(raw, list):
        raise TypeError("Relevance-label file has no preferences list")
    preferences: list[dict[str, object]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise TypeError("Every relevance-label preference must be an object")
        preferences.append(
            {
                "id": str(entry["id"]),
                "text": str(entry["text"]),
                "relevant_item_ids": [str(value) for value in entry["relevant_item_ids"]],
            }
        )
    return preferences
