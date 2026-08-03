"""Thin CLI for a no-cost end-to-end synthetic pilot."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from recllm_fairness.data.candidate_pool import build_candidate_pool
from recllm_fairness.personas.generator import generate_personas
from recllm_fairness.pipeline.services import (
    collect_queries,
    make_specs,
    pilot_cost_projection,
    synthetic_catalog,
    write_analysis_outputs,
    write_json,
)
from recllm_fairness.storage.manifest import query_output_root
from recllm_fairness.storage.schema import ExperimentProvenance
from recllm_fairness.utils.config import load_config
from recllm_fairness.utils.logging import configure_logging

app = typer.Typer(add_completion=False)


@app.command()
def main(config_dir: Path = Path("config")) -> None:
    config = load_config(config_dir)
    configure_logging(config["logging"]["level"])
    catalog = synthetic_catalog("movie", 60)
    pool_config = config["candidate_pool"]
    pool = build_candidate_pool(
        catalog,
        size=min(int(pool_config["size"]), len(catalog)),
        head_fraction=float(pool_config["head_fraction"]),
        mid_fraction=float(pool_config["mid_fraction"]),
        tail_fraction=float(pool_config["tail_fraction"]),
        seed=int(config["seed"]),
    )
    conditions = generate_personas(
        preferences={
            **config["preferences"],
            "movie": [
                {
                    "text": "character-driven drama and imaginative science fiction",
                    "relevant_item_ids": [
                        item.item_id
                        for item in catalog
                        if set(item.genres) & {"Drama", "Science Fiction"}
                    ],
                },
                {
                    "text": "clever comedy and suspenseful mystery",
                    "relevant_item_ids": [
                        item.item_id
                        for item in catalog
                        if set(item.genres) & {"Comedy", "Mystery"}
                    ],
                },
            ],
        },
        personas_per_cell=min(2, int(config["pilot_personas_per_cell"])),
        traits=config["traits"],
        levels=config["levels"],
        phrasing_variants=config["phrasing_variants"],
        domains=("movie",),
    )
    specs = make_specs(
        conditions,
        pool,
        model_name="mock",
        provenance=ExperimentProvenance(
            design_version="synthetic-smoke-v2",
            design_bundle_sha256="0" * 64,
            dataset_version="synthetic:60",
            collection_protocol_version="synthetic-smoke-v2",
        ),
        repeats=1,
        top_k=int(config["top_k"]),
    )
    output_root = query_output_root(
        config["storage"]["root"],
        design_version="synthetic-smoke-v2",
        stage="pilot",
        protocol_version="synthetic-smoke-v2",
    )
    queries = asyncio.run(
        collect_queries(
            specs,
            model_name="mock",
            model_config=config["models"]["mock"],
            catalog=catalog,
            output_root=output_root,
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
            fuzzy_threshold=float(config["matching"]["fuzzy_threshold"]),
            ambiguity_margin=float(config["matching"]["ambiguity_margin"]),
            hard_cap_usd=float(config["budget"]["hard_cap_usd"]),
            concurrency=int(config["concurrency"]),
        )
    )
    outputs = write_analysis_outputs(
        queries,
        catalog,
        k=int(config["top_k"]),
        table_dir="outputs/tables/pilot",
        bootstrap_resamples=200,
        confidence_level=float(config["statistics"]["confidence_level"]),
        seed=int(config["seed"]),
        alpha=float(config["statistics"]["alpha"]),
        rq3_minimum_effect=float(config["statistics"]["rq3_minimum_effect"]),
    )
    estimate = pilot_cost_projection(queries, full_query_count=len(specs))
    write_json(config["budget"]["pilot_estimate_path"], estimate)
    typer.echo(f"Pilot complete: {len(queries)} query records; outputs: {outputs}")


if __name__ == "__main__":
    app()
