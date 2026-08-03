"""Versioned output paths and resumable run-manifest provenance."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from recllm_fairness.storage.schema import SHA256_PATTERN, ExperimentProvenance
from recllm_fairness.utils.seeding import condition_seed

_SAFE_PART = re.compile(r"[^A-Za-z0-9_.-]")


def _safe_part(value: str) -> str:
    return _SAFE_PART.sub("_", value)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def query_output_root(
    storage_root: str | Path,
    *,
    design_version: str,
    stage: str,
    protocol_version: str,
    model: str | None = None,
    domain: str | None = None,
    legacy_unversioned: bool = False,
) -> Path:
    """Resolve an isolated query root without relocating frozen legacy artifacts."""
    root = Path(storage_root)
    if legacy_unversioned:
        result = root / stage / protocol_version
    else:
        result = (
            root
            / f"design={_safe_part(design_version)}"
            / f"stage={_safe_part(stage)}"
            / f"protocol={_safe_part(protocol_version)}"
        )
    if model is not None:
        result /= _safe_part(model) if legacy_unversioned else f"model={_safe_part(model)}"
    if domain is not None:
        result /= _safe_part(domain) if legacy_unversioned else f"domain={_safe_part(domain)}"
    return result


def analysis_output_root(
    table_root: str | Path,
    *,
    design_version: str,
    domain: str,
    models: list[str],
    analysis_version: str,
) -> Path:
    """Namespace tables by every dimension that can change manuscript evidence."""
    model_set = "+".join(_safe_part(model) for model in sorted(set(models)))
    return (
        Path(table_root)
        / f"design={_safe_part(design_version)}"
        / f"domain={_safe_part(domain)}"
        / f"models={model_set}"
        / f"analysis={_safe_part(analysis_version)}"
    )


class RunAttempt(BaseModel):
    model_config = ConfigDict(frozen=True)

    started_at: datetime
    ended_at: datetime | None = None
    status: Literal["in_progress", "completed", "failed"] = "in_progress"
    error: str | None = None


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
    design_version: str
    design_bundle_sha256: str = Field(pattern=SHA256_PATTERN)
    dataset_version: str
    collection_protocol_version: str
    stage: str
    model: str
    domain: str
    seed: int
    query_order_seed: int
    query_order_sha256: str = Field(pattern=SHA256_PATTERN)
    query_ids: list[str]
    environment_lock_path: str
    environment_lock_sha256: str = Field(pattern=SHA256_PATTERN)
    configured_model_digest: str
    resolved_model_digest: str | None = None
    host_hardware: dict[str, object]
    attempts: list[RunAttempt]


def hardware_snapshot() -> dict[str, object]:
    """Capture portable host facts and GPU identity when NVIDIA tooling is available."""
    snapshot: dict[str, object] = {
        "hostname": platform.node(),
        "operating_system": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
    }
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,uuid,driver_version,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        snapshot["gpus"] = []
    else:
        snapshot["gpus"] = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return snapshot


def query_order_digest(query_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(query_ids).encode()).hexdigest()


def manifest_seed(base_seed: int, provenance: ExperimentProvenance, model: str, domain: str) -> int:
    return condition_seed(base_seed, provenance.design_version, model, domain, "query-order")


def _write_manifest(path: Path, manifest: RunManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def start_run_manifest(
    path: str | Path,
    *,
    provenance: ExperimentProvenance,
    stage: str,
    model: str,
    domain: str,
    seed: int,
    query_ids: list[str],
    environment_lock: str | Path,
    configured_model_digest: str,
    hardware: dict[str, object] | None = None,
) -> RunManifest:
    """Create or validate a manifest and append a resumable execution attempt."""
    destination = Path(path)
    lock = Path(environment_lock).resolve()
    order_seed = manifest_seed(seed, provenance, model, domain)
    immutable = {
        **provenance.model_dump(),
        "stage": stage,
        "model": model,
        "domain": domain,
        "seed": seed,
        "query_order_seed": order_seed,
        "query_order_sha256": query_order_digest(query_ids),
        "query_ids": query_ids,
        "environment_lock_path": str(lock),
        "environment_lock_sha256": sha256_file(lock),
        "configured_model_digest": configured_model_digest,
    }
    if destination.exists():
        existing = RunManifest.model_validate_json(destination.read_text(encoding="utf-8"))
        observed = existing.model_dump(
            exclude={"resolved_model_digest", "host_hardware", "attempts"}
        )
        expected = {"schema_version": 1, **immutable}
        if observed != expected:
            raise ValueError("Existing run manifest is incompatible with the requested partition")
        attempts = [*existing.attempts, RunAttempt(started_at=datetime.now(UTC))]
        manifest = existing.model_copy(update={"attempts": attempts})
    else:
        manifest = RunManifest(
            **immutable,
            host_hardware=hardware if hardware is not None else hardware_snapshot(),
            attempts=[RunAttempt(started_at=datetime.now(UTC))],
        )
    _write_manifest(destination, manifest)
    return manifest


def finish_run_manifest(
    path: str | Path,
    *,
    status: Literal["completed", "failed"],
    resolved_model_digest: str | None = None,
    error: str | None = None,
) -> RunManifest:
    destination = Path(path)
    manifest = RunManifest.model_validate_json(destination.read_text(encoding="utf-8"))
    if not manifest.attempts or manifest.attempts[-1].status != "in_progress":
        raise ValueError("Run manifest has no in-progress attempt to finish")
    last = manifest.attempts[-1].model_copy(
        update={"ended_at": datetime.now(UTC), "status": status, "error": error}
    )
    updated = manifest.model_copy(
        update={
            "attempts": [*manifest.attempts[:-1], last],
            "resolved_model_digest": resolved_model_digest or manifest.resolved_model_digest,
        }
    )
    _write_manifest(destination, updated)
    return updated


def manifest_model_digest(model_snapshots: list[str]) -> str:
    unique = sorted(set(model_snapshots))
    if len(unique) != 1:
        raise ValueError(f"Partition contains multiple model snapshots: {unique}")
    snapshot = unique[0]
    return snapshot.rsplit("@", 1)[-1]


def manifest_summary(manifest: RunManifest) -> dict[str, Any]:
    """Small serializable view for operational logging and tests."""
    return {
        "design_version": manifest.design_version,
        "model": manifest.model,
        "domain": manifest.domain,
        "records": len(manifest.query_ids),
        "attempts": len(manifest.attempts),
        "status": manifest.attempts[-1].status,
    }
