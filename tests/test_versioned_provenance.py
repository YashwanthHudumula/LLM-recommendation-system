from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from recllm_fairness.pipeline.protocol import assert_collection_permitted
from recllm_fairness.storage.io import (
    IncompatibleDesignError,
    completed_keys,
    read_records,
)
from recllm_fairness.storage.manifest import (
    analysis_output_root,
    finish_run_manifest,
    query_output_root,
    start_run_manifest,
)
from recllm_fairness.storage.schema import ExperimentProvenance
from recllm_fairness.utils.config import load_config


def _legacy_row() -> dict[str, object]:
    return {
        "persona_id": "M1",
        "model": "mock",
        "domain": "movie",
        "trait": "openness",
        "trait_level": "high",
        "phrasing_variant": "direct",
        "repeat_idx": 0,
    }


def _provenance(version: str, digest_character: str) -> ExperimentProvenance:
    return ExperimentProvenance(
        design_version=version,
        design_bundle_sha256=digest_character * 64,
        dataset_version="MovieLens:25m",
        collection_protocol_version="closed-catalog-v2",
    )


def test_legacy_v1_remains_readable_but_cannot_resume_as_v2(tmp_path: Path) -> None:
    legacy = pd.DataFrame([_legacy_row()])
    legacy_path = tmp_path / "legacy.parquet"
    legacy.to_parquet(legacy_path, index=False)

    loaded = read_records(tmp_path)
    assert len(loaded) == 1
    assert completed_keys(loaded) == {
        ("M1", "mock", "movie", "openness", "high", "direct", 0)
    }
    with pytest.raises(IncompatibleDesignError, match="legacy or incomplete"):
        completed_keys(loaded, expected_provenance=_provenance("persona-relevance-v2-100", "b"))


def test_frozen_v2_still_blocks_full_collection_until_preflight() -> None:
    config = load_config("config", "config/full_run_v2_100.yaml")
    with pytest.raises(ValueError, match="does not permit 'full' collection"):
        assert_collection_permitted(config, stage="full")


def test_versioned_resume_rejects_a_different_design_bundle() -> None:
    v1 = _provenance("persona-relevance-v1", "a")
    frame = pd.DataFrame([{**v1.model_dump(), **_legacy_row()}])
    with pytest.raises(IncompatibleDesignError, match="incompatible experiment provenance"):
        completed_keys(
            frame,
            expected_provenance=_provenance("persona-relevance-v2-100", "b"),
        )


def test_v2_output_paths_include_design_and_analysis_dimensions(tmp_path: Path) -> None:
    queries = query_output_root(
        tmp_path / "queries",
        design_version="persona-relevance-v2-100",
        stage="full",
        protocol_version="closed-catalog-v2",
        model="qwen",
        domain="movie",
    )
    assert "design=persona-relevance-v2-100" in str(queries)
    assert "model=qwen" in str(queries)

    tables = analysis_output_root(
        tmp_path / "tables",
        design_version="persona-relevance-v2-100",
        domain="movie",
        models=["qwen", "gemma"],
        analysis_version="confirmatory-v1",
    )
    rendered = str(tables)
    assert "domain=movie" in rendered
    assert "models=gemma+qwen" in rendered
    assert "analysis=confirmatory-v1" in rendered


def test_run_manifest_is_resumable_and_records_environment_and_attempt_times(
    tmp_path: Path,
) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text("frozen dependencies\n", encoding="utf-8")
    path = tmp_path / "partition" / "run_manifest.json"
    provenance = _provenance("persona-relevance-v2-100", "c")
    hardware = {"hostname": "test-host", "gpus": ["test-gpu"]}

    first = start_run_manifest(
        path,
        provenance=provenance,
        stage="full",
        model="qwen",
        domain="movie",
        seed=7,
        query_ids=["q2", "q1"],
        environment_lock=lock,
        configured_model_digest="digest-prefix",
        hardware=hardware,
    )
    finish_run_manifest(path, status="failed", error="intentional interruption")
    resumed = start_run_manifest(
        path,
        provenance=provenance,
        stage="full",
        model="qwen",
        domain="movie",
        seed=7,
        query_ids=["q2", "q1"],
        environment_lock=lock,
        configured_model_digest="digest-prefix",
        hardware={"hostname": "ignored on resume"},
    )
    assert len(resumed.attempts) == 2
    completed = finish_run_manifest(
        path,
        status="completed",
        resolved_model_digest="full-digest",
    )
    assert completed.resolved_model_digest == "full-digest"
    assert completed.attempts[0].status == "failed"
    assert completed.attempts[0].ended_at is not None
    assert completed.attempts[1].status == "completed"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["host_hardware"] == hardware
    assert len(first.query_order_sha256) == 64


def test_run_manifest_rejects_query_order_drift(tmp_path: Path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text("lock", encoding="utf-8")
    path = tmp_path / "run_manifest.json"
    kwargs = {
        "provenance": _provenance("persona-relevance-v2-100", "d"),
        "stage": "full",
        "model": "qwen",
        "domain": "movie",
        "seed": 7,
        "environment_lock": lock,
        "configured_model_digest": "digest",
        "hardware": {},
    }
    start_run_manifest(path, query_ids=["q1", "q2"], **kwargs)
    with pytest.raises(ValueError, match="incompatible"):
        start_run_manifest(path, query_ids=["q2", "q1"], **kwargs)
