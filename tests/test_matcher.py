from __future__ import annotations

from recllm_fairness.data.catalog import Item
from recllm_fairness.parsing.matcher import match_titles
from recllm_fairness.parsing.response_parser import parse_response


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
