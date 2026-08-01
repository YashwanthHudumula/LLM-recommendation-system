from __future__ import annotations

import pandas as pd

from recllm_fairness.data.catalog import Item
from recllm_fairness.personas.relevance_labels import build_movie_labels, build_music_labels
from recllm_fairness.personas.traits import audit_marker_length_parity


def movie(item_id: str, genres: list[str], count: int) -> Item:
    return Item(
        item_id=item_id,
        domain="movie",
        title=f"Movie {item_id}",
        genres=genres,
        popularity_rank=int(item_id),
        popularity_tier="head",
        interaction_count=count,
    )


def test_movie_labels_apply_boolean_genre_rules_and_reliability_filter() -> None:
    labels = build_movie_labels(
        [
            movie("1", ["Romance", "Comedy"], 25),
            movie("2", ["Romance"], 30),
            movie("3", ["Romance", "Comedy"], 19),
        ],
        [
            {
                "id": "M2",
                "text": "romantic comedies",
                "genre_rule": {"all_of": ["Romance", "Comedy"]},
            }
        ],
        min_ratings=20,
        dataset_version="1m",
        design_version="test",
    )
    preference = labels["preferences"][0]
    assert preference["relevant_item_ids"] == ["1"]
    assert preference["relevant_count"] == 1


def test_music_labels_use_binary_cosine_and_listener_filters() -> None:
    pairs = pd.DataFrame(
        [
            ("u1", "seed", "Seed", "seed"),
            ("u2", "seed", "Seed", "seed"),
            ("u1", "near", "Near", "near"),
            ("u2", "near", "Near", "near"),
            ("u3", "near", "Near", "near"),
            ("u3", "far", "Far", "far"),
        ],
        columns=["user_id", "item_id", "artist_name", "normalized_artist_name"],
    )
    labels = build_music_labels(
        pairs,
        [{"id": "S1", "text": "seed taste", "seed_artists": ["Seed"]}],
        min_seed_listeners=2,
        min_candidate_listeners=2,
        cosine_threshold=0.5,
        acceptable_size=(1, 5),
        dataset_version="toy",
        design_version="test",
    )
    preference = labels["preferences"][0]
    assert preference["relevant_item_ids"] == ["near", "seed"]
    assert preference["within_acceptable_size"] is True


def test_trait_marker_lengths_pass_pre_registered_tolerance() -> None:
    report = audit_marker_length_parity(max_difference=3)
    assert all(row["difference"] <= 3 for row in report.values())
