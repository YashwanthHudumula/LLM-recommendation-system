"""Protocol gates shared by collection and analysis entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from recllm_fairness.storage.manifest import sha256_file
from recllm_fairness.storage.schema import ExperimentProvenance


def dataset_version(config: dict[str, Any], *, domain: str, stage: str) -> str:
    if domain == "movie":
        source = config["movielens"][stage]
        return f"MovieLens:{source['version']}"
    if domain == "music":
        source = config["lastfm"][stage]
        return f"LastFM:{source['version']}"
    raise ValueError("domain must be movie or music")


def experiment_provenance(
    config: dict[str, Any], *, domain: str, stage: str
) -> ExperimentProvenance:
    design = config.get("design")
    if not isinstance(design, dict):
        raise ValueError("Configuration is missing the versioned design block")
    bundle_sha256 = design.get("bundle_sha256")
    if not bundle_sha256:
        raise ValueError(
            f"Design {design.get('version', '<unknown>')} has no frozen bundle SHA256"
        )
    return ExperimentProvenance(
        design_version=str(design["version"]),
        design_bundle_sha256=str(bundle_sha256),
        dataset_version=dataset_version(config, domain=domain, stage=stage),
        collection_protocol_version=str(config["collection_protocol"]),
    )


def assert_collection_permitted(
    config: dict[str, Any], *, stage: str, persona_count: int | None = None
) -> None:
    """Fail closed until a design is frozen and explicitly permits the requested stage."""
    design = config.get("design")
    if not isinstance(design, dict):
        raise ValueError("Configuration is missing the versioned design block")
    if design.get("status") != "frozen":
        raise ValueError(f"Design {design.get('version')} is not frozen; collection is blocked")
    permitted = design.get("permitted_stages", [])
    if stage not in permitted:
        raise ValueError(
            f"Design {design.get('version')} does not permit {stage!r} collection"
        )
    expected = design.get("expected_personas", {}).get(stage)
    if expected is not None and persona_count is not None and persona_count != int(expected):
        raise ValueError(
            f"Design requires exactly {expected} {stage} personas; found {persona_count}"
        )


def validate_design_bundle(
    config: dict[str, Any], *, provenance: ExperimentProvenance
) -> Path:
    """Verify that the configured frozen bundle exists and matches the recorded digest."""
    design = config["design"]
    path = Path(str(design["bundle_path"]))
    if not path.exists():
        raise ValueError(f"Frozen design bundle does not exist: {path}")
    observed = sha256_file(path)
    if observed != provenance.design_bundle_sha256:
        raise ValueError(
            "Frozen design bundle checksum mismatch: "
            f"expected {provenance.design_bundle_sha256}, observed {observed}"
        )
    return path


def validate_label_artifact(
    path: str | Path,
    *,
    provenance: ExperimentProvenance,
    domain: str,
) -> dict[str, Any]:
    """Bind a label artifact to the same design and dataset as immutable query rows."""
    raw_document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_document, dict):
        raise TypeError("Relevance-label artifact must contain a JSON object")
    document = cast(dict[str, Any], raw_document)
    if document.get("design_version") != provenance.design_version:
        raise ValueError(
            "Relevance-label design mismatch: "
            f"expected {provenance.design_version}, observed {document.get('design_version')}"
        )
    if document.get("domain") != domain:
        raise ValueError(
            f"Relevance-label domain mismatch: expected {domain}, observed {document.get('domain')}"
        )
    dataset = document.get("dataset", {})
    observed_dataset = f"{dataset.get('name')}:{dataset.get('version')}"
    if observed_dataset != provenance.dataset_version:
        raise ValueError(
            "Relevance-label dataset mismatch: "
            f"expected {provenance.dataset_version}, observed {observed_dataset}"
        )
    return document


def legacy_unversioned_storage(config: dict[str, Any]) -> bool:
    design = config.get("design", {})
    return bool(design.get("legacy_unversioned_storage", False))
