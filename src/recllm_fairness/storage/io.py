"""Atomic append-only Parquet storage partitioned by experimental condition."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from recllm_fairness.storage.schema import (
    IDENTITY_COLUMNS,
    LEGACY_IDENTITY_COLUMNS,
    PROVENANCE_COLUMNS,
    ExperimentProvenance,
    QueryRecord,
)

_SAFE_PART = re.compile(r"[^A-Za-z0-9_.-]")


def _partition_value(value: str) -> str:
    return _SAFE_PART.sub("_", value)


def record_path(root: str | Path, record: QueryRecord) -> Path:
    base = Path(root)
    model_partition = f"model={_partition_value(record.model)}"
    domain_partition = f"domain={record.domain}"
    suffix = base.parts[-2:]
    already_partitioned = suffix in {
        (model_partition, domain_partition),
        (_partition_value(record.model), record.domain),
    }
    partition = base if already_partitioned else base / model_partition / domain_partition
    return (
        partition
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


class IncompatibleDesignError(ValueError):
    """Raised before resume could mix records from incompatible experiments."""


def completed_keys(
    frame: pd.DataFrame,
    expected_provenance: ExperimentProvenance | None = None,
) -> set[tuple[object, ...]]:
    """Build resume keys while retaining read/resume support for legacy v1 tables."""
    if frame.empty:
        return set()
    present_provenance = set(PROVENANCE_COLUMNS) & set(frame.columns)
    if present_provenance and present_provenance != set(PROVENANCE_COLUMNS):
        missing = set(PROVENANCE_COLUMNS) - set(frame.columns)
        raise IncompatibleDesignError(
            f"Query table has incomplete provenance columns: {sorted(missing)}"
        )
    if expected_provenance is not None:
        missing = set(IDENTITY_COLUMNS) - set(frame.columns)
        if missing:
            raise IncompatibleDesignError(
                "Cannot resume a versioned collection from legacy or incomplete records; "
                f"missing identity columns: {sorted(missing)}"
            )
        observed = frame[PROVENANCE_COLUMNS].drop_duplicates()
        expected = expected_provenance.identity_values()
        observed_values = set(observed.itertuples(index=False, name=None))
        if observed_values != {expected}:
            raise IncompatibleDesignError(
                "Existing records have incompatible experiment provenance: "
                f"expected {expected}, observed {sorted(observed_values)}"
            )
        identity_columns = IDENTITY_COLUMNS
    elif present_provenance:
        identity_columns = IDENTITY_COLUMNS
    else:
        missing_legacy = set(LEGACY_IDENTITY_COLUMNS) - set(frame.columns)
        if missing_legacy:
            raise ValueError(
                f"Query table is missing identity columns: {sorted(missing_legacy)}"
            )
        identity_columns = LEGACY_IDENTITY_COLUMNS
    if frame.duplicated(identity_columns).any():
        raise ValueError("Duplicate experimental condition records detected")
    return set(frame[identity_columns].itertuples(index=False, name=None))


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
