"""Opportunity-adjusted sensitivity CLI over a frozen paired-analysis package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from recllm_fairness.pipeline.services import (
    bootstrap_opportunity_metric_deltas,
    compute_condition_opportunity_metrics,
    load_configured_catalog,
    load_paired_analysis_queries,
    opportunity_metric_deltas,
    write_json,
)
from recllm_fairness.storage.manifest import analysis_output_root, sha256_file
from recllm_fairness.utils.config import load_config

app = typer.Typer(add_completion=False)


@app.command()
def main(
    source_package: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    analysis_version: str = typer.Option(...),
    bootstrap_resamples: int = typer.Option(..., min=1),
    config_dir: Path = Path("config"),
    config_override: Path | None = None,
) -> None:
    config = load_config(config_dir, config_override)
    source_manifest_path = source_package / "analysis_manifest.json"
    paired_path = source_package / "user_side_similarities.csv"
    if not source_manifest_path.is_file() or not paired_path.is_file():
        raise typer.BadParameter("Source package lacks its manifest or paired query table")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    queries = load_paired_analysis_queries(paired_path)
    if len(queries) != int(source_manifest["query_records"]):
        raise typer.BadParameter("Paired table does not exactly reconstruct source query count")
    domains = queries["domain"].drop_duplicates().tolist()
    if len(domains) != 1:
        raise typer.BadParameter("Source package must contain exactly one domain")
    domain = str(domains[0])
    catalog = load_configured_catalog(config, domain=domain, stage="full")
    models = queries["model"].drop_duplicates().astype(str).tolist()
    destination = analysis_output_root(
        config["analysis"]["table_root"],
        design_version=str(source_manifest["design_version"]),
        domain=domain,
        models=models,
        analysis_version=analysis_version,
    )
    if destination.exists() and any(destination.iterdir()):
        raise typer.BadParameter(f"Analysis output already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    metrics = compute_condition_opportunity_metrics(queries, catalog, k=int(config["top_k"]))
    deltas = opportunity_metric_deltas(metrics)
    intervals = bootstrap_opportunity_metric_deltas(
        queries,
        catalog,
        k=int(config["top_k"]),
        n_resamples=bootstrap_resamples,
        confidence_level=float(config["statistics"]["confidence_level"]),
        seed=int(config["seed"]),
    )
    tables = {
        "opportunity_adjusted_metrics": metrics,
        "opportunity_adjusted_deltas": deltas,
        "opportunity_adjusted_delta_bootstrap_cis": intervals,
    }
    for name, frame in tables.items():
        frame.to_csv(destination / f"{name}.csv", index=False)
    protocol = Path(str(config["analysis"]["opportunity_protocol_path"]))
    write_json(
        destination / "analysis_manifest.json",
        {
            "analysis_version": analysis_version,
            "analysis_view": source_manifest.get("analysis_view", "primary"),
            "bootstrap_resamples": bootstrap_resamples,
            "design_version": source_manifest["design_version"],
            "domain": domain,
            "models": sorted(models),
            "query_records": len(queries),
            "source_analysis_package": str(source_package.resolve()),
            "source_manifest_sha256": sha256_file(source_manifest_path),
            "source_paired_table_sha256": sha256_file(paired_path),
            "opportunity_protocol_path": str(protocol.resolve()),
            "opportunity_protocol_sha256": sha256_file(protocol),
        },
    )
    typer.echo(f"Opportunity analysis complete: {destination}")


if __name__ == "__main__":
    app()
