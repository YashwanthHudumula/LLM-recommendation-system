from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from recllm_fairness.data.catalog import Item
from recllm_fairness.metrics.aggregate import (
    aggregate_exposure,
    candidate_opportunity_counts,
    exposure_counts,
)
from recllm_fairness.metrics.relevance import ndcg_at_k, precision_at_k
from recllm_fairness.pipeline.services import (
    bootstrap_opportunity_metric_deltas,
    compute_condition_opportunity_metrics,
    load_paired_analysis_queries,
    opportunity_metric_deltas,
    select_analysis_view,
)


def test_aggregate_exposure_preserves_condition_and_rank() -> None:
    queries = pd.DataFrame(
        [
            {
                "query_id": "q1",
                "persona_id": "p1",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "matched_item_ids": ["a", "b", "c"],
            },
            {
                "query_id": "q2",
                "persona_id": "p2",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "matched_item_ids": ["a", "c"],
            },
        ]
    )
    exploded = aggregate_exposure(queries, k=2)
    assert exploded["item_id"].tolist() == ["a", "b", "a", "c"]
    assert exploded["rank"].tolist() == [1, 2, 1, 2]
    counts = exposure_counts(exploded)
    assert counts.set_index("item_id").loc["a", "exposure_count"] == 2


def test_candidate_opportunity_counts_queries_not_raw_pool_union() -> None:
    queries = pd.DataFrame(
        [
            {
                "query_id": "q1",
                "persona_id": "p1",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "candidate_item_ids": ["a", "b"],
            },
            {
                "query_id": "q2",
                "persona_id": "p2",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "candidate_item_ids": ["a", "c"],
            },
        ]
    )

    counts = candidate_opportunity_counts(queries).set_index("item_id")["opportunity_count"]
    assert counts.to_dict() == {"a": 2, "b": 1, "c": 1}


def test_condition_opportunity_metrics_and_paired_bootstrap() -> None:
    catalog = [
        Item(
            item_id=item_id,
            domain="movie",
            title=item_id,
            popularity_rank=index,
            popularity_tier="tail" if item_id in {"c", "d"} else "head",
        )
        for index, item_id in enumerate(["a", "b", "c", "d"], 1)
    ]
    common = {
        "model": "m",
        "domain": "movie",
        "phrasing_variant": "direct",
        "repeat_idx": 0,
    }
    queries = pd.DataFrame(
        [
            {
                **common,
                "query_id": "n1",
                "persona_id": "p1",
                "trait": "neutral",
                "trait_level": "neutral",
                "candidate_item_ids": ["a", "b", "c", "d"],
                "matched_item_ids": ["a", "c"],
            },
            {
                **common,
                "query_id": "n2",
                "persona_id": "p2",
                "trait": "neutral",
                "trait_level": "neutral",
                "candidate_item_ids": ["a", "b"],
                "matched_item_ids": ["a", "b"],
            },
            {
                **common,
                "query_id": "s1",
                "persona_id": "p1",
                "trait": "openness",
                "trait_level": "high",
                "candidate_item_ids": ["a", "b", "c", "d"],
                "matched_item_ids": ["b", "d"],
            },
            {
                **common,
                "query_id": "s2",
                "persona_id": "p2",
                "trait": "openness",
                "trait_level": "high",
                "candidate_item_ids": ["a", "b"],
                "matched_item_ids": ["b", "a"],
            },
        ]
    )

    metrics = compute_condition_opportunity_metrics(queries, catalog, k=2)
    neutral = metrics.loc[metrics["trait_level"].eq("neutral")].iloc[0]
    assert neutral["eligible_item_count"] == 4
    assert neutral["candidate_opportunities"] == pytest.approx(6)
    assert neutral["opportunity_coverage"] == pytest.approx(3 / 4)
    assert neutral["opportunity_long_tail_coverage"] == pytest.approx(1 / 2)

    deltas = opportunity_metric_deltas(metrics)
    assert len(deltas) == 1
    assert deltas.iloc[0]["delta_opportunity_coverage"] == pytest.approx(0)

    intervals = bootstrap_opportunity_metric_deltas(
        queries,
        catalog,
        k=2,
        n_resamples=10,
        confidence_level=0.95,
        seed=7,
    )
    assert set(intervals["metric"]) == {
        "opportunity_gini",
        "opportunity_hhi",
        "opportunity_normalized_hhi",
        "opportunity_coverage",
        "opportunity_long_tail_coverage",
    }
    assert intervals["n_resamples"].eq(10).all()


def test_paired_analysis_table_reconstructs_neutral_rows(tmp_path: Path) -> None:
    paired = pd.DataFrame(
        [
            {
                "query_id": "s1",
                "persona_id": "p1",
                "model": "m",
                "domain": "movie",
                "trait": "openness",
                "trait_level": "high",
                "phrasing_variant": "direct",
                "repeat_idx": "0",
                "candidate_item_ids": "['a' 'b' 'c']",
                "matched_item_ids": "['a' 'b']",
                "neutral_items": "['a' 'c']",
            },
            {
                "query_id": "s2",
                "persona_id": "p1",
                "model": "m",
                "domain": "movie",
                "trait": "agreeableness",
                "trait_level": "low",
                "phrasing_variant": "direct",
                "repeat_idx": "0",
                "candidate_item_ids": "['a' 'b' 'c']",
                "matched_item_ids": "['b' 'c']",
                "neutral_items": "['a' 'c']",
            },
        ]
    )
    path = tmp_path / "paired.csv"
    paired.to_csv(path, index=False)

    reconstructed = load_paired_analysis_queries(path)

    assert len(reconstructed) == 3
    neutral = reconstructed.loc[reconstructed["trait_level"].eq("neutral")].iloc[0]
    assert neutral["candidate_item_ids"] == ["a", "b", "c"]
    assert neutral["matched_item_ids"] == ["a", "c"]


def test_relevance_metrics_have_hand_computed_values() -> None:
    assert precision_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(2 / 3)
    expected = (1 + 1 / math.log2(4)) / (1 + 1 / math.log2(3))
    assert ndcg_at_k(["a", "x", "b"], {"a", "b"}, 3) == pytest.approx(expected)


def test_preregistered_analysis_views_filter_only_derived_rows() -> None:
    identity = {
        "model": "model",
        "domain": "movie",
        "phrasing_variant": "direct",
        "repeat_idx": 0,
    }
    queries = pd.DataFrame(
        [
            {
                **identity,
                "query_id": "neutral-exact",
                "persona_id": "p1",
                "trait_level": "neutral",
                "matched_item_ids": ["a", "b"],
                "hallucinated_titles": [],
                "off_list_titles": [],
            },
            {
                **identity,
                "query_id": "sensitive-exact",
                "persona_id": "p1",
                "trait_level": "high",
                "matched_item_ids": ["a", "b"],
                "hallucinated_titles": [],
                "off_list_titles": [],
            },
            {
                **identity,
                "query_id": "neutral-short",
                "persona_id": "p2",
                "trait_level": "neutral",
                "matched_item_ids": ["a"],
                "hallucinated_titles": [],
                "off_list_titles": [],
            },
            {
                **identity,
                "query_id": "orphan-exact",
                "persona_id": "p2",
                "trait_level": "high",
                "matched_item_ids": ["a", "b"],
                "hallucinated_titles": [],
                "off_list_titles": [],
            },
            {
                **identity,
                "query_id": "flagged-exact",
                "persona_id": "p1",
                "trait_level": "low",
                "matched_item_ids": ["a", "b"],
                "hallucinated_titles": ["invented"],
                "off_list_titles": [],
            },
        ]
    )

    exact = select_analysis_view(queries, view="exact-10-grounded", k=2)
    unflagged = select_analysis_view(queries, view="exclude-flagged-records", k=2)

    assert exact["query_id"].tolist() == [
        "neutral-exact",
        "sensitive-exact",
        "flagged-exact",
    ]
    assert unflagged["query_id"].tolist() == [
        "neutral-exact",
        "sensitive-exact",
        "neutral-short",
        "orphan-exact",
    ]
    assert len(queries) == 5
