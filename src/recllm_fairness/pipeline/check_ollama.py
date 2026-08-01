"""Small no-cost compatibility benchmark for frozen local Ollama manifests."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, cast

import typer

from recllm_fairness.models.ollama_client import OllamaClient
from recllm_fairness.models.registry import create_client
from recllm_fairness.parsing.matcher import match_titles
from recllm_fairness.parsing.response_parser import parse_response
from recllm_fairness.personas.generator import PersonaCondition
from recllm_fairness.personas.relevance_labels import load_label_preferences
from recllm_fairness.pipeline.services import (
    build_persona_candidate_pools,
    load_configured_catalog,
    write_json,
)
from recllm_fairness.prompting.builder import build_prompt
from recllm_fairness.utils.config import load_config

app = typer.Typer(add_completion=False)
DEFAULT_MODELS = "ollama_qwen3_8b,ollama_gemma3_12b,ollama_llama3_1_8b"
MINIMUM_PARSE_YIELD = 0.8


async def benchmark(
    config: dict[str, Any], model_names: list[str], domain: Literal["movie", "music"]
) -> dict[str, Any]:
    catalog = load_configured_catalog(config, domain=domain, stage="pilot")
    pool_config = config["candidate_pool"]
    labels = load_label_preferences(config["relevance_labels"]["pilot"][domain])
    conditions: list[PersonaCondition] = []
    for preference in labels:
        raw_relevant = preference["relevant_item_ids"]
        if not isinstance(raw_relevant, Sequence) or isinstance(raw_relevant, str):
            raise TypeError("Compatibility preference relevant_item_ids must be a sequence")
        conditions.append(
            PersonaCondition(
                persona_id=f"compatibility-{preference['id']}",
                domain=domain,
                stated_preferences=str(preference["text"]),
                relevant_item_ids=tuple(str(value) for value in raw_relevant),
                trait="neutral",
                trait_level="neutral",
                trait_marker="",
                phrasing_variant="direct",
            )
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
    results: list[dict[str, Any]] = []
    for model_name in model_names:
        client = create_client(model_name, config["models"])
        if not isinstance(client, OllamaClient):
            raise ValueError(f"Compatibility benchmark only accepts Ollama configs: {model_name}")
        query_results: list[dict[str, Any]] = []
        model_snapshot = ""
        for condition in conditions:
            pool = pools[condition.persona_id]
            prompt = build_prompt(condition, pool, top_k=int(config["top_k"]))
            response = await client.complete(
                prompt.system_prompt,
                prompt.user_prompt,
                float(config["temperature"]),
                min(200, int(config["max_tokens"])),
            )
            model_snapshot = response.model
            parsed = parse_response(response.text)
            matched = match_titles(
                parsed,
                catalog,
                allowed_item_ids=pool.item_ids,
                threshold=float(config["matching"]["fuzzy_threshold"]),
                ambiguity_margin=float(config["matching"]["ambiguity_margin"]),
            )
            raw = response.raw
            eval_duration = int(raw.get("eval_duration", 0))
            parse_yield = len(matched.matched_item_ids) / int(config["top_k"])
            query_results.append(
                {
                    "persona_id": condition.persona_id,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_duration_seconds": int(raw.get("total_duration", 0))
                    / 1_000_000_000,
                    "generation_tokens_per_second": (
                        response.completion_tokens / (eval_duration / 1_000_000_000)
                        if eval_duration
                        else None
                    ),
                    "raw_response_text": response.text,
                    "parsed_titles": parsed,
                    "matched_item_ids": matched.matched_item_ids,
                    "hallucinated_titles": matched.hallucinated_titles,
                    "off_list_titles": matched.off_list_titles,
                    "parse_yield": parse_yield,
                    "passed": parse_yield >= MINIMUM_PARSE_YIELD
                    and not matched.hallucinated_titles
                    and not matched.off_list_titles,
                }
            )
        runtime = await client.runtime_status()
        await client.unload()
        result = {
            "config_name": model_name,
            "model_snapshot": model_snapshot,
            "queries": query_results,
            "size_vram_bytes": None if runtime is None else runtime.get("size_vram"),
            "loaded_size_bytes": None if runtime is None else runtime.get("size"),
            "context_length": None if runtime is None else runtime.get("context_length"),
        }
        result["passed"] = all(bool(query["passed"]) for query in query_results)
        results.append(result)
        await client.aclose()
    return {
        "schema_version": 2,
        "collection_protocol": config["collection_protocol"],
        "domain": domain,
        "purpose": "technical compatibility only; not a scientific result",
        "candidate_pool_size": int(pool_config["size"]),
        "preferences_tested": len(conditions),
        "top_k": int(config["top_k"]),
        "pass_criteria": {
            "minimum_parse_yield": MINIMUM_PARSE_YIELD,
            "maximum_hallucinated_titles": 0,
            "maximum_off_list_titles": 0,
            "note": "Scientific pilot gates use repeated-query condition-level rates.",
        },
        "all_passed": all(bool(result["passed"]) for result in results),
        "models": results,
    }


@app.command()
def main(
    config_dir: Path = Path("config"),
    models: str = typer.Option(DEFAULT_MODELS, help="Comma-separated enabled Ollama keys"),
    domain: str = typer.Option("movie", help="movie or music"),
    output: Path = Path("data/audits/ollama_closed_catalog_compatibility_v2.json"),
) -> None:
    config = load_config(config_dir)
    if domain not in {"movie", "music"}:
        raise typer.BadParameter("domain must be movie or music")
    model_names = [value.strip() for value in models.split(",") if value.strip()]
    report = asyncio.run(
        benchmark(config, model_names, cast(Literal["movie", "music"], domain))
    )
    write_json(output, report)
    for result in report["models"]:
        queries = result["queries"]
        matched = sum(len(query["matched_item_ids"]) for query in queries)
        expected = len(queries) * int(report["top_k"])
        typer.echo(
            f"{result['config_name']}: passed={result['passed']} "
            f"matched={matched}/{expected}"
        )
    if not report["all_passed"]:
        raise typer.Exit(code=1)
    typer.echo(f"Compatibility report: {output}")


if __name__ == "__main__":
    app()
