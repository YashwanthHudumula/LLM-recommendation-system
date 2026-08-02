"""Analysis CLI; deliberately contains no model client imports or calls."""

from __future__ import annotations

from pathlib import Path

import typer

from recllm_fairness.pipeline.services import (
    load_configured_catalog,
    reground_queries,
    synthetic_catalog,
    write_analysis_outputs,
)
from recllm_fairness.storage.io import read_records
from recllm_fairness.utils.config import load_config

app = typer.Typer(add_completion=False)


@app.command()
def main(
    config_dir: Path = Path("config"),
    query_root: Path | None = None,
    domain: str | None = typer.Option(None, help="Required when the query root has both domains"),
    stage: str = typer.Option("pilot", help="pilot or full when query-root is omitted"),
) -> None:
    config = load_config(config_dir)
    if stage not in {"pilot", "full"}:
        raise typer.BadParameter("stage must be pilot or full")
    root = query_root or (
        Path(config["storage"]["root"]) / stage / str(config["collection_protocol"])
    )
    queries = read_records(root)
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
    outputs = write_analysis_outputs(
        queries,
        catalog,
        k=int(config["top_k"]),
        table_dir="outputs/tables/analysis",
        bootstrap_resamples=int(config["statistics"]["bootstrap_resamples"]),
        confidence_level=float(config["statistics"]["confidence_level"]),
        seed=int(config["seed"]),
        alpha=float(config["statistics"]["alpha"]),
        rq3_minimum_effect=float(config["statistics"]["rq3_minimum_effect"]),
    )
    typer.echo(f"Analysis complete: {outputs}")


if __name__ == "__main__":
    app()
