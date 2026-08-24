"""Guarded fairness-prompt mitigation after the primary RQ1-RQ4 analysis."""

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
from recllm_fairness.pipeline.protocol import (
    assert_collection_permitted,
    experiment_provenance,
    legacy_unversioned_storage,
    validate_design_bundle,
    validate_label_artifact,
)
from recllm_fairness.pipeline.services import (
    build_persona_candidate_pools,
    collect_queries,
    load_configured_catalog,
    make_specs,
)
from recllm_fairness.storage.io import read_records
from recllm_fairness.storage.manifest import query_output_root
from recllm_fairness.utils.config import load_config
from recllm_fairness.utils.costs import BudgetGuard

app = typer.Typer(add_completion=False)


@app.command()
def main(
    model: str = typer.Option(...),
    domain: str = typer.Option(...),
    config_dir: Path = Path("config"),
    config_override: Path | None = None,
    results: Path = Path("outputs/tables/analysis/item_side_metrics.csv"),
) -> None:
    if not results.exists():
        raise typer.BadParameter("Run and review the primary RQ1-RQ4 analysis before mitigation")
    if domain not in {"movie", "music"}:
        raise typer.BadParameter("domain must be movie or music")
    domain_literal = cast(Literal["movie", "music"], domain)
    config = load_config(config_dir, config_override)
    if model not in config["models"]:
        raise typer.BadParameter(f"Unknown model config: {model}")
    model_config = config["models"][model]
    assert_collection_permitted(config, stage="full")
    provenance = experiment_provenance(config, domain=domain, stage="full")
    validate_design_bundle(config, provenance=provenance)
    if model_config["provider"] != "mock":
        encoder = load_sentence_transformer(config["semantic_check"]["model_name"])
        check_phrasing_equivalence(
            encoder,
            threshold=float(config["semantic_check"]["minimum_cosine_similarity"]),
            domain=domain,
            top_k=int(config["top_k"]),
        )
    catalog = load_configured_catalog(config, domain=domain, stage="full")
    pool_config = config["candidate_pool"]
    label_path = Path(config["relevance_labels"]["full"][domain])
    if not label_path.exists():
        raise typer.BadParameter(f"Missing fixed full-scale relevance labels: {label_path}")
    validate_label_artifact(label_path, provenance=provenance, domain=domain)
    domain_preferences = load_label_preferences(label_path)
    assert_collection_permitted(
        config,
        stage="full",
        persona_count=len(domain_preferences),
    )
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
        provenance=provenance,
        repeats=int(config["repeats"]),
        top_k=int(config["top_k"]),
        fairness_instruction=True,
    )
    protocol = str(config["collection_protocol"])
    prior = read_records(
        query_output_root(
            config["storage"]["root"],
            design_version=provenance.design_version,
            stage="full",
            protocol_version=protocol,
            legacy_unversioned=legacy_unversioned_storage(config),
        )
    )
    prior_spend = float(prior["cost_usd"].sum()) if not prior.empty and "cost_usd" in prior else 0.0
    estimate_path = Path("outputs/tables") / f"pilot_cost_estimate_{protocol}_{model}_{domain}.json"
    if model_config["provider"] != "mock":
        if not estimate_path.exists():
            raise typer.BadParameter(f"Missing pilot cost estimate: {estimate_path}")
        estimate = json.loads(estimate_path.read_text(encoding="utf-8"))
        unique_calls = len({(spec.prompt_sha256, spec.repeat_idx) for spec in specs})
        projected = prior_spend + float(estimate["average_cost_per_unique_call_usd"]) * unique_calls
        BudgetGuard(float(config["budget"]["hard_cap_usd"])).preflight(projected)
    root = query_output_root(
        config["storage"]["root"],
        design_version=provenance.design_version,
        stage="mitigation",
        protocol_version=protocol,
        model=model,
        domain=domain,
        legacy_unversioned=False,
    )
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
            initial_spent_usd=prior_spend,
        )
    )
    typer.echo(f"Mitigation collection complete: {len(queries)} records under {root}")


if __name__ == "__main__":
    app()
