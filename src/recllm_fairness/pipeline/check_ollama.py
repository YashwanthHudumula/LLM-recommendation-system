"""Small no-cost compatibility benchmark for frozen local Ollama manifests."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import typer

from recllm_fairness.data.candidate_pool import build_candidate_pool
from recllm_fairness.models.ollama_client import OllamaClient
from recllm_fairness.models.registry import create_client
from recllm_fairness.parsing.matcher import match_titles
from recllm_fairness.parsing.response_parser import parse_response
from recllm_fairness.personas.generator import PersonaCondition
from recllm_fairness.personas.relevance_labels import load_label_preferences
from recllm_fairness.pipeline.services import load_configured_catalog, write_json
from recllm_fairness.prompting.builder import build_prompt
from recllm_fairness.utils.config import load_config

app = typer.Typer(add_completion=False)
DEFAULT_MODELS = "ollama_qwen3_8b,ollama_gemma3_12b,ollama_llama3_1_8b"
MINIMUM_PARSE_YIELD = 0.8


async def benchmark(config: dict[str, Any], model_names: list[str]) -> dict[str, Any]:
    catalog = load_configured_catalog(config, domain="movie", stage="pilot")
    pool_config = config["candidate_pool"]
    pool = build_candidate_pool(
        catalog,
        size=min(30, int(pool_config["size"])),
        head_fraction=float(pool_config["head_fraction"]),
        mid_fraction=float(pool_config["mid_fraction"]),
        tail_fraction=float(pool_config["tail_fraction"]),
        seed=int(config["seed"]),
    )
    labels = load_label_preferences(config["relevance_labels"]["pilot"]["movie"])
    preference = labels[0]
    raw_relevant = preference["relevant_item_ids"]
    if not isinstance(raw_relevant, Sequence) or isinstance(raw_relevant, str):
        raise TypeError("Compatibility preference relevant_item_ids must be a sequence")
    condition = PersonaCondition(
        persona_id="compatibility-M1",
        domain="movie",
        stated_preferences=str(preference["text"]),
        relevant_item_ids=tuple(str(value) for value in raw_relevant),
        trait="neutral",
        trait_level="neutral",
        trait_marker="",
        phrasing_variant="direct",
    )
    prompt = build_prompt(condition, pool, top_k=int(config["top_k"]))
    results: list[dict[str, Any]] = []
    for model_name in model_names:
        client = create_client(model_name, config["models"])
        if not isinstance(client, OllamaClient):
            raise ValueError(f"Compatibility benchmark only accepts Ollama configs: {model_name}")
        response = await client.complete(
            prompt.system_prompt,
            prompt.user_prompt,
            float(config["temperature"]),
            min(200, int(config["max_tokens"])),
        )
        parsed = parse_response(response.text)
        matched = match_titles(
            parsed,
            catalog,
            allowed_item_ids=pool.item_ids,
            threshold=float(config["matching"]["fuzzy_threshold"]),
            ambiguity_margin=float(config["matching"]["ambiguity_margin"]),
        )
        runtime = await client.runtime_status()
        await client.unload()
        raw = response.raw
        eval_duration = int(raw.get("eval_duration", 0))
        result = {
            "config_name": model_name,
            "model_snapshot": response.model,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_duration_seconds": int(raw.get("total_duration", 0)) / 1_000_000_000,
            "load_duration_seconds": int(raw.get("load_duration", 0)) / 1_000_000_000,
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
            "size_vram_bytes": None if runtime is None else runtime.get("size_vram"),
            "loaded_size_bytes": None if runtime is None else runtime.get("size"),
            "context_length": None if runtime is None else runtime.get("context_length"),
        }
        parse_yield = len(matched.matched_item_ids) / int(config["top_k"])
        result["parse_yield"] = parse_yield
        result["passed"] = (
            parse_yield >= MINIMUM_PARSE_YIELD
            and not matched.hallucinated_titles
            and not matched.off_list_titles
        )
        results.append(result)
        await client.aclose()
    return {
        "schema_version": 1,
        "purpose": "technical compatibility only; not a scientific result",
        "candidate_pool_size": len(pool.items),
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
    output: Path = Path("data/audits/ollama_compatibility_v1.json"),
) -> None:
    config = load_config(config_dir)
    model_names = [value.strip() for value in models.split(",") if value.strip()]
    report = asyncio.run(benchmark(config, model_names))
    write_json(output, report)
    for result in report["models"]:
        typer.echo(
            f"{result['config_name']}: passed={result['passed']} "
            f"matched={len(result['matched_item_ids'])}/{report['top_k']} "
            f"seconds={result['total_duration_seconds']:.1f}"
        )
    if not report["all_passed"]:
        raise typer.Exit(code=1)
    typer.echo(f"Compatibility report: {output}")


if __name__ == "__main__":
    app()
