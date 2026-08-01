from __future__ import annotations

import pandas as pd
import pytest

from recllm_fairness.metrics.user_side import (
    jaccard_at_k,
    pafs,
    paired_similarities,
    prag_at_k,
    serp_at_k,
    snsr,
    snsv,
)


def test_hand_computed_list_similarities() -> None:
    neutral = ["a", "b", "c"]
    sensitive = ["a", "x", "c"]
    assert jaccard_at_k(neutral, sensitive, 3) == pytest.approx(0.5)
    assert serp_at_k(neutral, sensitive, 3) == pytest.approx(6 / 24)
    assert prag_at_k(neutral, sensitive, 3) == pytest.approx(2 / 3)


def test_hand_computed_fairness_summaries() -> None:
    values = [0.2, 0.4]
    assert snsr(values) == pytest.approx(0.2)
    assert snsv(values) == pytest.approx(0.1)
    assert pafs(values) == pytest.approx(0.9)


def test_query_rows_pair_with_the_exact_neutral_baseline() -> None:
    common = {
        "persona_id": "p1",
        "model": "m",
        "domain": "movie",
        "phrasing_variant": "direct",
        "repeat_idx": 0,
    }
    frame = pd.DataFrame(
        [
            {
                **common,
                "trait": "neutral",
                "trait_level": "neutral",
                "matched_item_ids": ["a", "b", "c"],
            },
            {
                **common,
                "trait": "openness",
                "trait_level": "high",
                "matched_item_ids": ["a", "x", "c"],
            },
        ]
    )
    result = paired_similarities(frame, k=3)
    assert len(result) == 1
    assert result.loc[0, "jaccard"] == pytest.approx(0.5)


@pytest.mark.published_ballpark
def test_published_fairllm_music_prag_range_table_sanity() -> None:
    # FaiRLLM Table 1 reports max=.7997, min=.7293 and SNSR=.0705 (rounding).
    assert snsr([0.7997, 0.7293]) == pytest.approx(0.0705, abs=1e-4)
