"""Analysis CLI; deliberately contains no model client imports or calls."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from recllm_fairness.pipeline.protocol import legacy_unversioned_storage
from recllm_fairness.pipeline.services import (
    AnalysisView,
    load_configured_catalog,
    reground_queries,
    select_analysis_view,
    synthetic_catalog,
    write_analysis_outputs,
    write_json,
)
from recllm_fairness.storage.io import read_records
from recllm_fairness.storage.manifest import analysis_output_root, query_output_root, sha256_file
from recllm_fairness.utils.config import load_config

app = typer.Typer(add_completion=False)


@app.command()
def main(
    config_dir: Path = Path("config"),
    config_override: Path | None = None,
    query_root: Path | None = None,
    domain: str | None = typer.Option(None, help="Required when the query root has both domains"),
    stage: str = typer.Option("pilot", help="pilot or full when query-root is omitted"),
    analysis_version: str | None = None,
    sensitivity: str = "primary",
    opportunity_bootstrap_resamples: int | None = typer.Option(
        None, help="Persona-bootstrap draws for opportunity-adjusted deltas"
    ),
) -> None:
    config = load_config(config_dir, config_override)
    valid_views = {"primary", "exact-10-grounded", "exclude-flagged-records"}
    if sensitivity not in valid_views:
        raise typer.BadParameter(f"sensitivity must be one of {sorted(valid_views)}")
    selected_view = cast(AnalysisView, sensitivity)
    if stage not in {"pilot", "full"}:
        raise typer.BadParameter("stage must be pilot or full")
    configured_design = str(config["design"]["version"])
    root = query_root or query_output_root(
        config["storage"]["root"],
        design_version=configured_design,
        stage=stage,
        protocol_version=str(config["collection_protocol"]),
        legacy_unversioned=legacy_unversioned_storage(config),
    )
    queries = read_records(root, filters={"domain": domain} if domain is not None else None)
    if queries.empty:
        raise typer.BadParameter(f"No query records found under {root}")
    if domain is not None:
        if domain not in {"movie", "music"}:
            raise typer.BadParameter("domain must be movie or music")
        queries = queries.loc[queries["domain"] == domain].reset_index(drop=True)
    domains = queries["domain"].drop_duplicates().tolist()
    if len(domains) != 1:
        raise typer.BadParameter("Select one domain for analysis with --domain")
    selected_domain = str(domains[0])
    if "design_version" in queries:
        design_versions = queries["design_version"].drop_duplicates().astype(str).tolist()
        if len(design_versions) != 1:
            raise typer.BadParameter(f"Query root mixes design versions: {design_versions}")
        selected_design = design_versions[0]
        for column in (
            "design_bundle_sha256",
            "dataset_version",
            "collection_protocol_version",
        ):
            if queries[column].nunique(dropna=False) != 1:
                raise typer.BadParameter(f"Query root mixes incompatible {column} values")
    else:
        selected_design = configured_design
    synthetic = all(
        str(item_id).startswith(f"{selected_domain}-")
        for item_id in queries["candidate_item_ids"].explode().dropna()
    )
    catalog = (
        synthetic_catalog(selected_domain, 60)
        if synthetic
        else load_configured_catalog(config, domain=selected_domain, stage=stage)
    )
    queries = reground_queries(
        queries,
        catalog,
        fuzzy_threshold=float(config["matching"]["fuzzy_threshold"]),
        ambiguity_margin=float(config["matching"]["ambiguity_margin"]),
    )
    source_query_records = len(queries)
    queries = select_analysis_view(queries, view=selected_view, k=int(config["top_k"]))
    if queries.empty:
        raise typer.BadParameter(f"Analysis view {sensitivity!r} retained no query records")
    models = queries["model"].drop_duplicates().astype(str).tolist()
    selected_analysis_version = analysis_version or str(config["analysis"]["version"])
    table_dir = analysis_output_root(
        config["analysis"]["table_root"],
        design_version=selected_design,
        domain=selected_domain,
        models=models,
        analysis_version=selected_analysis_version,
    )
    if table_dir.exists() and any(table_dir.iterdir()):
        raise typer.BadParameter(
            f"Analysis output already exists: {table_dir}. Use a new --analysis-version."
        )
    outputs = write_analysis_outputs(
        queries,
        catalog,
        k=int(config["top_k"]),
        table_dir=table_dir,
        bootstrap_resamples=int(config["statistics"]["bootstrap_resamples"]),
        confidence_level=float(config["statistics"]["confidence_level"]),
        seed=int(config["seed"]),
        alpha=float(config["statistics"]["alpha"]),
        rq3_minimum_effect=float(config["statistics"]["rq3_minimum_effect"]),
        opportunity_bootstrap_resamples=opportunity_bootstrap_resamples,
    )
    opportunity_protocol = Path(str(config["analysis"]["opportunity_protocol_path"]))
    write_json(
        table_dir / "analysis_manifest.json",
        {
            "design_version": selected_design,
            "domain": selected_domain,
            "models": sorted(models),
            "analysis_version": selected_analysis_version,
            "analysis_view": selected_view,
            "source_query_root": str(root.resolve()),
            "source_query_records": source_query_records,
            "query_records": len(queries),
            "opportunity_protocol_path": str(opportunity_protocol.resolve()),
            "opportunity_protocol_sha256": sha256_file(opportunity_protocol),
            "opportunity_bootstrap_resamples": (
                opportunity_bootstrap_resamples or int(config["statistics"]["bootstrap_resamples"])
            ),
        },
    )
    typer.echo(f"Analysis complete: {outputs}")


if __name__ == "__main__":
    app()
