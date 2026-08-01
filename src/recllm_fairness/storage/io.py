"""Atomic append-only Parquet storage partitioned by experimental condition."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from recllm_fairness.storage.schema import IDENTITY_COLUMNS, QueryRecord

_SAFE_PART = re.compile(r"[^A-Za-z0-9_.-]")


def _partition_value(value: str) -> str:
    return _SAFE_PART.sub("_", value)


def record_path(root: str | Path, record: QueryRecord) -> Path:
    base = Path(root)
    return (
        base
        / f"model={_partition_value(record.model)}"
        / f"domain={record.domain}"
        / f"trait={_partition_value(record.trait)}"
        / f"trait_level={record.trait_level}"
        / f"{_partition_value(record.query_id)}.parquet"
    )


def append_record(root: str | Path, record: QueryRecord) -> Path:
    """Atomically persist one immutable query; reject duplicate query IDs."""
    destination = record_path(root, record)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Query record already exists: {destination}")
    frame = pd.DataFrame([record.model_dump(mode="python")])
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{record.query_id}-", suffix=".parquet", dir=destination.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        frame.to_parquet(temporary, index=False, engine="pyarrow")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def read_records(root: str | Path, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """Read records safely without relying on inferred Hive partition types."""
    paths = sorted(Path(root).glob("**/*.parquet"))
    if not paths:
        return pd.DataFrame(columns=list(QueryRecord.model_fields))
    frame = pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True)
    for column, value in (filters or {}).items():
        if column not in frame:
            raise KeyError(f"Unknown query-record filter column: {column}")
        frame = frame.loc[frame[column] == value]
    return frame.reset_index(drop=True)


def completed_keys(frame: pd.DataFrame) -> set[tuple[object, ...]]:
    """Build the exact resumability key set from an existing query table."""
    if frame.empty:
        return set()
    missing = set(IDENTITY_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Query table is missing identity columns: {sorted(missing)}")
    if frame.duplicated(IDENTITY_COLUMNS).any():
        raise ValueError("Duplicate experimental condition records detected")
    return set(frame[IDENTITY_COLUMNS].itertuples(index=False, name=None))


def condition_diagnostics(frame: pd.DataFrame) -> pd.DataFrame:
    """Return hallucination, off-list, token, and cost outputs per condition."""
    if frame.empty:
        return pd.DataFrame()
    data = frame.copy()
    data["parsed_count"] = data["parsed_titles"].map(len)
    data["hallucination_count"] = data["hallucinated_titles"].map(len)
    data["off_list_count"] = data["off_list_titles"].map(len)
    data["hallucination_rate"] = data["hallucination_count"] / data["parsed_count"].clip(lower=1)
    data["off_list_rate"] = data["off_list_count"] / data["parsed_count"].clip(lower=1)
    group = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    return (
        data.groupby(group, dropna=False)
        .agg(
            queries=("query_id", "count"),
            hallucination_rate=("hallucination_rate", "mean"),
            off_list_rate=("off_list_rate", "mean"),
            prompt_tokens=("prompt_tokens", "sum"),
            completion_tokens=("completion_tokens", "sum"),
            cost_usd=("cost_usd", "sum"),
        )
        .reset_index()
    )

