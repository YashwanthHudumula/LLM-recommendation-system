"""Thin, resumable pilot/full collection CLI with semantic and budget gates."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Literal, cast

import typer

from recllm_fairness.personas.generator import generate_personas
from recllm_fairness.personas.relevance_labels import load_label_preferences
from recllm_fairness.personas.semantic_check import (
    check_phrasing_equivalence,
    load_sentence_transformer,
)
from recllm_fairness.pipeline.services import (
    build_persona_candidate_pools,
    collect_queries,
    load_configured_catalog,
    make_specs,
    pilot_cost_projection,
    write_json,
)
from recllm_fairness.utils.config import load_config
from recllm_fairness.utils.costs import BudgetGuard
from recllm_fairness.utils.logging import configure_logging

app = typer.Typer(add_completion=False)


@app.command()
def main(
    config_dir: Path = Path("config"),
    model: str = typer.Option(..., help="Enabled key from config/models.yaml"),
    domain: str = typer.Option(..., help="movie or music"),
    stage: str = typer.Option("pilot", help="pilot or full"),
) -> None:
    config = load_config(config_dir)
    configure_logging(config["logging"]["level"])
    if domain not in {"movie", "music"}:
        raise typer.BadParameter("domain must be movie or music")
    domain_literal = cast(Literal["movie", "music"], domain)
    if stage not in {"pilot", "full"}:
        raise typer.BadParameter("stage must be pilot or full")
    if model not in config["models"]:
        raise typer.BadParameter(f"Unknown model config: {model}")
    model_config = config["models"][model]
    if model_config["provider"] != "mock":
        encoder = load_sentence_transformer(config["semantic_check"]["model_name"])
        result = check_phrasing_equivalence(
            encoder,
            threshold=float(config["semantic_check"]["minimum_cosine_similarity"]),
            domain=domain,
            top_k=int(config["top_k"]),
        )
        typer.echo(
            f"Semantic phrasing gate passed (minimum cosine={result.minimum_similarity:.3f})"
        )

    catalog = load_configured_catalog(config, domain=domain, stage=stage)
    pool_config = config["candidate_pool"]
    label_path = Path(config["relevance_labels"][stage][domain])
    if not label_path.exists():
        raise typer.BadParameter(
            f"Missing fixed relevance labels: {label_path}. "
            f"Run recllm-build-labels --stage {stage} first."
        )
    domain_preferences = load_label_preferences(label_path)
    repeats = 1 if stage == "pilot" else int(config["repeats"])
    conditions = generate_personas(
        preferences={domain: domain_preferences},
        personas_per_cell=len(domain_preferences),
        traits=config["traits"],
        levels=config["levels"],
        phrasing_variants=config["phrasing_variants"],
        domains=(domain_literal,),
    )
    pools = build_persona_candidate_pools(
        conditions,
        catalog,
        size=int(pool_config["size"]),
        head_fraction=float(pool_config["head_fraction"]),
        mid_fraction=float(pool_config["mid_fraction"]),
        tail_fraction=float(pool_config["tail_fraction"]),
        relevant_fraction=float(pool_config["relevant_fraction"]),
        top_k=int(config["top_k"]),
        seed=int(config["seed"]),
        shuffle_items=bool(pool_config["shuffle_items"]),
    )
    specs = make_specs(
        conditions,
        pools,
        model_name=model,
        repeats=repeats,
        top_k=int(config["top_k"]),
    )
    protocol = str(config["collection_protocol"])
    estimate_path = (
        Path("outputs/tables") / f"pilot_cost_estimate_{protocol}_{model}_{domain}.json"
    )
    unique_calls = len({(spec.prompt_sha256, spec.repeat_idx) for spec in specs})
    if stage == "full" and model_config["provider"] != "mock":
        if not estimate_path.exists():
            raise typer.BadParameter(
                f"Missing same-model/domain pilot estimate: {estimate_path}. "
                "Run --stage pilot first."
            )
        estimate = json.loads(estimate_path.read_text(encoding="utf-8"))
        projected = float(estimate["average_cost_per_unique_call_usd"]) * unique_calls
        BudgetGuard(float(config["budget"]["hard_cap_usd"])).preflight(projected)
        typer.echo(f"Budget gate passed: projected full cost ${projected:.2f}")

    root = Path(config["storage"]["root"]) / stage / protocol / model / domain
    queries = asyncio.run(
        collect_queries(
            specs,
            model_name=model,
            model_config=model_config,
            catalog=catalog,
            output_root=root,
            temperature=float(config["temperature"]),
            max_tokens=int(config["max_tokens"]),
            fuzzy_threshold=float(config["matching"]["fuzzy_threshold"]),
            ambiguity_margin=float(config["matching"]["ambiguity_margin"]),
            hard_cap_usd=float(config["budget"]["hard_cap_usd"]),
            concurrency=int(model_config.get("concurrency", config["concurrency"])),
        )
    )
    if stage == "pilot":
        write_json(estimate_path, pilot_cost_projection(queries, unique_calls))
    typer.echo(f"Collection complete: {len(queries)} immutable records under {root}")


if __name__ == "__main__":
    app()
