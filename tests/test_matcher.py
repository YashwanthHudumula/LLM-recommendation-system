from __future__ import annotations

import pandas as pd

from recllm_fairness.data.catalog import Item
from recllm_fairness.parsing.matcher import match_titles
from recllm_fairness.parsing.response_parser import parse_response
from recllm_fairness.pipeline.services import reground_queries


def _catalog() -> list[Item]:
    return [
        Item(
            item_id="1",
            domain="movie",
            title="Spirited Away",
            genres=["Animation"],
            popularity_rank=1,
            popularity_tier="head",
        ),
        Item(
            item_id="2",
            domain="movie",
            title="The Matrix",
            genres=["Science Fiction"],
            popularity_rank=2,
            popularity_tier="mid",
        ),
        Item(
            item_id="3",
            domain="movie",
            title="Moonlight",
            genres=["Drama"],
            popularity_rank=3,
            popularity_tier="tail",
        ),
    ]


def test_parser_handles_numbered_and_json_outputs() -> None:
    assert parse_response('1. "Spirited Away"\n2. The Matrix') == ["Spirited Away", "The Matrix"]
    assert parse_response('[{"title": "Moonlight"}, "The Matrix"]') == [
        "Moonlight",
        "The Matrix",
    ]
    assert parse_response("1. Star Wars: Episode IV - A New Hope") == [
        "Star Wars: Episode IV - A New Hope"
    ]
    assert parse_response("1. C042 | Star Wars: Episode IV - A New Hope") == [
        "Star Wars: Episode IV - A New Hope"
    ]
    assert parse_response("C042 | Star Wars: Episode IV - A New Hope") == [
        "Star Wars: Episode IV - A New Hope"
    ]
    assert parse_response("C042 | Blade Runner (does not match, skipped)") == ["Blade Runner"]


def test_matcher_separates_hallucinated_and_off_list_titles() -> None:
    result = match_titles(
        ["Spirited Away", "The Matrx", "Moonlight", "Invented Film"],
        _catalog(),
        allowed_item_ids={"1", "2"},
        threshold=80,
    )
    assert result.matched_item_ids == ["1", "2"]
    assert result.off_list_titles == ["Moonlight"]
    assert result.hallucinated_titles == ["Invented Film"]


def test_matcher_prefers_allowed_id_for_exact_duplicate_title() -> None:
    catalog = _catalog()
    duplicate = catalog[0].model_copy(update={"item_id": "4", "popularity_rank": 4})
    result = match_titles(
        ["Spirited Away"],
        [*catalog, duplicate],
        allowed_item_ids={"4"},
    )
    assert result.matched_item_ids == ["4"]
    assert result.hallucinated_titles == []
    assert result.off_list_titles == []


def test_matcher_accepts_only_verbatim_allowed_title_with_annotation_suffix() -> None:
    annotated = match_titles(
        ["Spirited Away (Note: selected for its atmosphere)"],
        _catalog(),
        allowed_item_ids={"1"},
    )
    assert annotated.matched_item_ids == ["1"]
    assert annotated.hallucinated_titles == []
    assert annotated.off_list_titles == []

    not_a_prefix = match_titles(
        ["Spirited Awayward"],
        _catalog(),
        allowed_item_ids={"1"},
        threshold=100.0,
    )
    assert not_a_prefix.matched_item_ids == []
    assert not_a_prefix.hallucinated_titles == ["Spirited Awayward"]


def test_reground_queries_rebuilds_derived_matches_from_immutable_raw_text() -> None:
    catalog = _catalog()
    duplicate = catalog[0].model_copy(update={"item_id": "4", "popularity_rank": 4})
    frame = pd.DataFrame(
        [
            {
                "raw_response_text": "C001 | Spirited Away",
                "candidate_item_ids": ["4"],
                "parsed_titles": [],
                "matched_item_ids": [],
                "hallucinated_titles": ["Spirited Away"],
                "off_list_titles": [],
            }
        ]
    )
    result = reground_queries(
        frame,
        [*catalog, duplicate],
        fuzzy_threshold=88.0,
        ambiguity_margin=3.0,
    )
    assert result.loc[0, "matched_item_ids"] == ["4"]
    assert result.loc[0, "hallucinated_titles"] == []
    assert result.loc[0, "grounding_version"] == "allowed-title-annotation-v3"
