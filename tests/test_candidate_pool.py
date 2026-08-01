from __future__ import annotations

import pytest

from recllm_fairness.data.candidate_pool import build_candidate_pool
from recllm_fairness.pipeline.services import synthetic_catalog


def test_candidate_pool_is_deterministic_and_stratified() -> None:
    catalog = synthetic_catalog(size=30)
    kwargs = dict(
        size=12,
        head_fraction=0.5,
        mid_fraction=0.25,
        tail_fraction=0.25,
        seed=42,
    )
    first = build_candidate_pool(catalog, **kwargs)
    second = build_candidate_pool(catalog, **kwargs)
    assert first.item_ids == second.item_ids
    assert [item.item_id for item in first.items] == [item.item_id for item in second.items]
    assert len(first.items) == 12
    assert [item.popularity_rank for item in first.items[:6]] == list(range(1, 7))
    assert sum(item.popularity_tier == "mid" for item in first.items) == 3
    assert sum(item.popularity_tier == "tail" for item in first.items) == 3


def test_candidate_pool_rejects_invalid_fractions() -> None:
    with pytest.raises(ValueError, match="sum to one"):
        build_candidate_pool(
            synthetic_catalog(size=12),
            size=6,
            head_fraction=0.5,
            mid_fraction=0.5,
            tail_fraction=0.5,
            seed=1,
        )


def test_candidate_pool_guarantees_required_opportunity_and_can_shuffle() -> None:
    catalog = synthetic_catalog(size=60)
    required = {item.item_id for item in catalog if item.popularity_rank % 2 == 0}
    pool = build_candidate_pool(
        catalog,
        size=24,
        head_fraction=0.5,
        mid_fraction=0.25,
        tail_fraction=0.25,
        seed=7,
        required_item_ids=required,
        minimum_required=10,
        shuffle_items=True,
    )
    assert len(pool.items) == 24
    assert len(pool.item_ids.intersection(required)) >= 10
    assert sum(item.popularity_tier == "head" for item in pool.items) == 12
    assert sum(item.popularity_tier == "mid" for item in pool.items) == 6
    assert sum(item.popularity_tier == "tail" for item in pool.items) == 6
    assert [item.popularity_rank for item in pool.items[:12]] != list(range(1, 13))
    assert pool.prompt_block().splitlines()[0].startswith("C001 | ")
