from __future__ import annotations

import asyncio
from pathlib import Path

from recllm_fairness.data.candidate_pool import build_candidate_pool
from recllm_fairness.personas.generator import generate_personas
from recllm_fairness.pipeline.services import (
    collect_queries,
    make_specs,
    relevance_table,
    synthetic_catalog,
)


def test_collection_is_append_only_resumable_and_relevance_ready(tmp_path: Path) -> None:
    catalog = synthetic_catalog(size=12)
    pool = build_candidate_pool(
        catalog,
        size=12,
        head_fraction=0.5,
        mid_fraction=0.25,
        tail_fraction=0.25,
        seed=3,
    )
    conditions = generate_personas(
        preferences={
            "movie": [
                {
                    "text": "dramatic films",
                    "relevant_item_ids": [
                        item.item_id for item in catalog if "Drama" in item.genres
                    ],
                }
            ]
        },
        personas_per_cell=1,
        traits=["openness"],
        levels=["low", "neutral", "high"],
        phrasing_variants=["direct"],
        domains=("movie",),
    )
    specs = make_specs(conditions, pool, model_name="mock", repeats=1, top_k=3)
    kwargs = dict(
        specs=specs,
        model_name="mock",
        model_config={
            "provider": "mock",
            "model": "deterministic-catalog-v1",
            "enabled": True,
            "requests_per_minute": 100,
            "input_cost_per_million": 0.0,
            "output_cost_per_million": 0.0,
        },
        catalog=catalog,
        pool=pool,
        output_root=tmp_path,
        temperature=0.7,
        max_tokens=100,
        fuzzy_threshold=88.0,
        ambiguity_margin=3.0,
        hard_cap_usd=1.0,
        concurrency=2,
    )
    first = asyncio.run(collect_queries(**kwargs))
    second = asyncio.run(collect_queries(**kwargs))
    assert len(first) == len(second) == 3
    assert len(list(tmp_path.glob("**/*.parquet"))) == 3
    relevance = relevance_table(second, k=3)
    assert relevance["relevance_labels_available"].all()
    assert relevance["precision_at_k"].between(0, 1).all()
