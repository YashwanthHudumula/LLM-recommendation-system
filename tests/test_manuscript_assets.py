from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from recllm_fairness.pipeline.build_manuscript_assets import _scenario_table, _verify_sources


def test_verify_sources_accepts_exact_hash_and_rejects_mutation(tmp_path: Path) -> None:
    source = tmp_path / "audit.json"
    source.write_text("{}\n", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    spec = {"source_audits": {"test": {"path": str(source), "sha256": digest}}}
    _verify_sources(spec)
    source.write_text('{"changed": true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        _verify_sources(spec)


def test_scenario_table_includes_zero_count_categories() -> None:
    source = pd.DataFrame(
        {
            "domain": ["movie", "movie", "music"],
            "model": ["m1", "m1", "m2"],
            "scenario": ["concordant", "inverse", None],
        }
    )
    result = _scenario_table(source)
    movie = result[(result["domain"] == "movie") & (result["model"] == "m1")].iloc[0]
    music = result[(result["domain"] == "music") & (result["model"] == "m2")].iloc[0]
    assert movie[["concordant", "independent", "inverse", "undefined", "total"]].tolist() == [
        1,
        0,
        1,
        0,
        2,
    ]
    assert music["undefined"] == 1
    assert music["total"] == 1
