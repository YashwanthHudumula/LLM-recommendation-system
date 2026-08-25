"""Reusable orchestration services; CLI entrypoints contain no research logic."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import time
import warnings
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from recllm_fairness.data.candidate_pool import CandidatePool, build_candidate_pool
from recllm_fairness.data.catalog import Item
from recllm_fairness.data.lastfm import load_lastfm
from recllm_fairness.data.movielens import load_movielens
from recllm_fairness.metrics.aggregate import aggregate_exposure, exposure_counts
from recllm_fairness.metrics.item_side import (
    average_recommendation_popularity,
    catalog_coverage,
    dgu,
    gini_index,
    group_unfairness,
    hhi,
    long_tail_coverage,
    mgu,
    opportunity_adjusted_gini,
    opportunity_adjusted_hhi,
    opportunity_adjusted_normalized_hhi,
    within_opportunity_coverage,
)
from recllm_fairness.metrics.relevance import ndcg_at_k, precision_at_k
from recllm_fairness.metrics.user_side import paired_similarities
from recllm_fairness.models.base_client import LLMClient
from recllm_fairness.models.registry import create_client
from recllm_fairness.parsing.matcher import TitleMatcher
from recllm_fairness.parsing.response_parser import parse_response
from recllm_fairness.personas.generator import PersonaCondition, assert_counterfactual_control
from recllm_fairness.prompting.builder import PromptPair, build_prompt
from recllm_fairness.stats.correlation import spearman_fairness_scenario
from recllm_fairness.stats.mixed_effects import fit_mixed_effects
from recllm_fairness.stats.multiple_comparison import benjamini_hochberg
from recllm_fairness.storage.io import (
    append_record,
    completed_keys,
    condition_diagnostics,
    read_records,
)
from recllm_fairness.storage.manifest import manifest_seed
from recllm_fairness.storage.schema import IDENTITY_COLUMNS, ExperimentProvenance, QueryRecord
from recllm_fairness.utils.costs import BudgetGuard, Price

LOGGER = logging.getLogger(__name__)

AnalysisView = Literal["primary", "exact-10-grounded", "exclude-flagged-records"]

OPPORTUNITY_METRIC_COLUMNS = [
    "opportunity_gini",
    "opportunity_hhi",
    "opportunity_normalized_hhi",
    "opportunity_coverage",
    "opportunity_long_tail_coverage",
]

_QUOTED_ITEM_ID = re.compile(r"'([^']*)'")


@dataclass(frozen=True)
class QuerySpec:
    condition: PersonaCondition
    repeat_idx: int
    prompt: PromptPair
    prompt_sha256: str
    query_id: str
    candidate_pool: CandidatePool
    model_name: str
    provenance: ExperimentProvenance

    @property
    def identity(self) -> tuple[object, ...]:
        values = {
            **self.provenance.model_dump(),
            "persona_id": self.condition.persona_id,
            "model": self.model_name,
            "domain": self.condition.domain,
            "trait": self.condition.trait,
            "trait_level": self.condition.trait_level,
            "phrasing_variant": self.condition.phrasing_variant,
            "repeat_idx": self.repeat_idx,
        }
        return tuple(values[column] for column in IDENTITY_COLUMNS)


class MinuteRateLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute must be positive")
        self.limit = requests_per_minute
        self.timestamps: list[float] = []
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self.lock:
            now = time.monotonic()
            self.timestamps = [stamp for stamp in self.timestamps if now - stamp < 60]
            if len(self.timestamps) >= self.limit:
                await asyncio.sleep(60 - (now - self.timestamps[0]))
                now = time.monotonic()
                self.timestamps = [stamp for stamp in self.timestamps if now - stamp < 60]
            self.timestamps.append(now)


def load_configured_catalog(config: dict[str, Any], *, domain: str, stage: str) -> list[Item]:
    """Load the configured pilot/full catalog with shared tier cutoffs."""
    if stage not in {"pilot", "full"}:
        raise ValueError("stage must be pilot or full")
    tiers = config["popularity_tiers"]
    kwargs = {
        "head_quantile": float(tiers["head_quantile"]),
        "mid_quantile": float(tiers["mid_quantile"]),
    }
    if domain == "movie":
        source = config["movielens"][stage]
        return load_movielens(source["root"], source["version"], **kwargs)
    if domain == "music":
        source = config["lastfm"][stage]
        return load_lastfm(source["root"], source["version"], **kwargs)
    raise ValueError("domain must be movie or music")


def synthetic_catalog(domain: str = "movie", size: int = 60) -> list[Item]:
    """Create a metadata-rich catalog exclusively for the no-cost pilot and unit tests."""
    if size < 6:
        raise ValueError("Synthetic catalog needs at least six items")
    genres = ["Drama", "Comedy", "Science Fiction", "Documentary", "Mystery"]
    catalog: list[Item] = []
    for index in range(size):
        position = index + 1
        fraction = position / size
        tier: Literal["head", "mid", "tail"] = (
            "head" if fraction <= 1 / 3 else "mid" if fraction <= 2 / 3 else "tail"
        )
        catalog.append(
            Item(
                item_id=f"{domain}-{position:04d}",
                domain="movie" if domain == "movie" else "music",
                title=f"Synthetic {'Film' if domain == 'movie' else 'Artist'} {position:04d}",
                genres=[genres[index % len(genres)]],
                provider_or_studio=f"Provider {index % 7}",
                popularity_rank=position,
                popularity_tier=tier,
                interaction_count=(size - index) ** 2,
                release_year=1980 + index % 45 if domain == "movie" else None,
            )
        )
    return catalog


def build_persona_candidate_pools(
    conditions: list[PersonaCondition],
    catalog: list[Item],
    *,
    size: int,
    head_fraction: float,
    mid_fraction: float,
    tail_fraction: float,
    relevant_fraction: float,
    top_k: int,
    seed: int,
    shuffle_items: bool,
) -> dict[str, CandidatePool]:
    """Fix one relevance-aware opportunity pool per base persona across counterfactuals."""
    if not 0 <= relevant_fraction <= 1:
        raise ValueError("relevant_fraction must be between zero and one")
    assert_counterfactual_control(conditions)
    relevant_by_persona = {
        condition.persona_id: condition.relevant_item_ids for condition in conditions
    }
    required = max(top_k, round(size * relevant_fraction))
    return {
        persona_id: build_candidate_pool(
            catalog,
            size=size,
            head_fraction=head_fraction,
            mid_fraction=mid_fraction,
            tail_fraction=tail_fraction,
            seed=seed,
            required_item_ids=relevant_ids,
            minimum_required=required,
            shuffle_items=shuffle_items,
        )
        for persona_id, relevant_ids in relevant_by_persona.items()
    }


def make_specs(
    conditions: list[PersonaCondition],
    pool: CandidatePool | Mapping[str, CandidatePool],
    *,
    model_name: str,
    provenance: ExperimentProvenance,
    repeats: int,
    top_k: int,
    fairness_instruction: bool = False,
) -> list[QuerySpec]:
    assert_counterfactual_control(conditions)
    specs: list[QuerySpec] = []
    for condition in conditions:
        condition_pool = pool[condition.persona_id] if isinstance(pool, Mapping) else pool
        prompt = build_prompt(
            condition,
            condition_pool,
            top_k=top_k,
            fairness_instruction=fairness_instruction,
        )
        digest = hashlib.sha256(
            (prompt.system_prompt + "\0" + prompt.user_prompt).encode()
        ).hexdigest()
        for repeat_idx in range(repeats):
            identity = "|".join(
                [
                    *provenance.identity_values(),
                    condition.persona_id,
                    model_name,
                    condition.domain,
                    condition.trait,
                    condition.trait_level,
                    condition.phrasing_variant,
                    str(repeat_idx),
                ]
            )
            query_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
            specs.append(
                QuerySpec(
                    condition,
                    repeat_idx,
                    prompt,
                    digest,
                    query_id,
                    condition_pool,
                    model_name,
                    provenance,
                )
            )
    return specs


def deterministic_query_order(specs: list[QuerySpec], *, seed: int) -> list[QuerySpec]:
    """Return a stable randomized schedule for one model/domain partition."""
    if not specs:
        return []
    models = {spec.model_name for spec in specs}
    domains = {spec.condition.domain for spec in specs}
    provenances = {spec.provenance for spec in specs}
    if len(models) != 1 or len(domains) != 1 or len(provenances) != 1:
        raise ValueError("Query ordering requires exactly one model, domain, and provenance")
    model = next(iter(models))
    domain = next(iter(domains))
    provenance = next(iter(provenances))
    ordered = list(specs)
    random.Random(manifest_seed(seed, provenance, model, domain)).shuffle(ordered)
    return ordered


async def collect_queries(
    specs: list[QuerySpec],
    *,
    model_name: str,
    model_config: dict[str, Any],
    catalog: list[Item],
    output_root: str | Path,
    temperature: float,
    max_tokens: int,
    fuzzy_threshold: float,
    ambiguity_margin: float,
    hard_cap_usd: float,
    concurrency: int,
    initial_spent_usd: float = 0.0,
    minimum_grounded_items_before_retry: int = 0,
    underlength_retry_instruction: str | None = None,
    retry_temperature: float = 0.0,
) -> pd.DataFrame:
    """Collect grouped identical prompts once, write all condition records, and resume safely."""
    if not specs:
        return read_records(output_root)
    provenances = {spec.provenance for spec in specs}
    spec_models = {spec.model_name for spec in specs}
    if len(provenances) != 1 or spec_models != {model_name}:
        raise ValueError("Collection specs must share one provenance and requested model")
    provenance = next(iter(provenances))
    existing = read_records(output_root)
    done = completed_keys(existing, expected_provenance=provenance)
    pending = [spec for spec in specs if spec.identity not in done]
    if not pending:
        LOGGER.info("All %d requested conditions are already complete", len(specs))
        return existing

    client: LLMClient = create_client(model_name, {model_name: model_config})
    input_price = model_config.get("input_cost_per_million")
    output_price = model_config.get("output_cost_per_million")
    if input_price is None or output_price is None:
        raise ValueError("Real collection requires recorded input/output prices")
    price = Price(float(input_price), float(output_price))
    already_spent = initial_spent_usd + float(
        existing.get("cost_usd", pd.Series(dtype=float)).sum()
    )
    budget = BudgetGuard(hard_cap_usd, already_spent)
    limiter = MinuteRateLimiter(int(model_config["requests_per_minute"]))
    semaphore = asyncio.Semaphore(concurrency)
    budget_lock = asyncio.Lock()
    title_matcher = TitleMatcher(catalog)
    groups: dict[tuple[str, int], list[QuerySpec]] = defaultdict(list)
    for spec in pending:
        groups[(spec.prompt_sha256, spec.repeat_idx)].append(spec)

    async def execute(group: list[QuerySpec]) -> None:
        representative = group[0]
        conservative_prompt_tokens = (
            len((representative.prompt.system_prompt + representative.prompt.user_prompt).split())
            * 2
        )
        conservative_cost = price.cost(conservative_prompt_tokens, max_tokens)
        async with semaphore:
            async with budget_lock:
                budget.reserve(conservative_cost)
            await limiter.acquire()
            response = await client.complete(
                representative.prompt.system_prompt,
                representative.prompt.user_prompt,
                temperature,
                max_tokens,
            )
            actual_cost = price.cost(response.prompt_tokens, response.completion_tokens)
            async with budget_lock:
                budget.record(actual_cost)
            parsed = parse_response(response.text)
            matched = title_matcher.match(
                parsed,
                allowed_item_ids=representative.candidate_pool.item_ids,
                threshold=fuzzy_threshold,
                ambiguity_margin=ambiguity_margin,
            )
            response_attempts = [response.text]
            attempt_temperatures = [temperature]
            retry_user_prompt: str | None = None
            total_prompt_tokens = response.prompt_tokens
            total_completion_tokens = response.completion_tokens
            total_cost = actual_cost
            if (
                underlength_retry_instruction
                and minimum_grounded_items_before_retry > 0
                and len(matched.matched_item_ids) < minimum_grounded_items_before_retry
            ):
                retry_user_prompt = (
                    representative.prompt.user_prompt + "\n\n" + underlength_retry_instruction
                )
                async with budget_lock:
                    budget.reserve(conservative_cost)
                await limiter.acquire()
                retry_response = await client.complete(
                    representative.prompt.system_prompt,
                    retry_user_prompt,
                    retry_temperature,
                    max_tokens,
                )
                retry_cost = price.cost(
                    retry_response.prompt_tokens, retry_response.completion_tokens
                )
                async with budget_lock:
                    budget.record(retry_cost)
                response = retry_response
                response_attempts.append(response.text)
                attempt_temperatures.append(retry_temperature)
                total_prompt_tokens += response.prompt_tokens
                total_completion_tokens += response.completion_tokens
                total_cost += retry_cost
                parsed = parse_response(response.text)
                matched = title_matcher.match(
                    parsed,
                    allowed_item_ids=representative.candidate_pool.item_ids,
                    threshold=fuzzy_threshold,
                    ambiguity_margin=ambiguity_margin,
                )
            for index, spec in enumerate(group):
                record = QueryRecord(
                    query_id=spec.query_id,
                    **spec.provenance.model_dump(),
                    persona_id=spec.condition.persona_id,
                    model=model_name,
                    model_snapshot=response.model,
                    domain=spec.condition.domain,
                    trait=spec.condition.trait,
                    trait_level=spec.condition.trait_level,
                    phrasing_variant=spec.condition.phrasing_variant,
                    stated_preferences=spec.condition.stated_preferences,
                    relevant_item_ids=list(spec.condition.relevant_item_ids),
                    repeat_idx=spec.repeat_idx,
                    system_prompt=spec.prompt.system_prompt,
                    user_prompt=spec.prompt.user_prompt,
                    prompt_sha256=spec.prompt_sha256,
                    candidate_item_ids=[
                        item.item_id for item in representative.candidate_pool.items
                    ],
                    raw_response_text=response.text,
                    response_attempts=response_attempts,
                    selected_attempt_idx=len(response_attempts) - 1,
                    retry_user_prompt=retry_user_prompt,
                    attempt_temperatures=attempt_temperatures,
                    parsed_titles=parsed,
                    matched_item_ids=matched.matched_item_ids,
                    hallucinated_titles=matched.hallucinated_titles,
                    off_list_titles=matched.off_list_titles,
                    prompt_tokens=total_prompt_tokens if index == 0 else 0,
                    completion_tokens=total_completion_tokens if index == 0 else 0,
                    cost_usd=total_cost if index == 0 else 0.0,
                )
                append_record(output_root, record)

    await asyncio.gather(*(execute(group) for group in groups.values()))
    close = getattr(client, "aclose", None)
    if close is not None:
        await close()
    return read_records(output_root)


def compute_condition_item_metrics(
    queries: pd.DataFrame, catalog: list[Item], *, k: int
) -> pd.DataFrame:
    exposures = aggregate_exposure(queries, k=k)
    counts = exposure_counts(exposures)
    catalog_ids = [item.item_id for item in catalog]
    tail_ids = [item.item_id for item in catalog if item.popularity_tier == "tail"]
    item_by_id = {item.item_id: item for item in catalog}
    popularity = {
        item.item_id: float(item.interaction_count or (1 / item.popularity_rank))
        for item in catalog
    }
    rows: list[dict[str, object]] = []
    condition_columns = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    for condition, group in counts.groupby(condition_columns, dropna=False):
        by_item = dict(zip(group["item_id"], group["exposure"], strict=True))
        vector = [float(by_item.get(item_id, 0.0)) for item_id in catalog_ids]
        recommended = [
            item_id
            for item_id, count in zip(group["item_id"], group["exposure_count"], strict=True)
            for _ in range(int(count))
        ]
        mask = pd.Series(True, index=queries.index)
        for column, value in zip(condition_columns, condition, strict=True):
            mask &= queries[column] == value
        condition_queries = queries.loc[mask]
        candidate_ids = set(
            item_id for values in condition_queries["candidate_item_ids"] for item_id in values
        )
        rec_tiers = Counter(item_by_id[item_id].popularity_tier for item_id in recommended)
        ref_tiers = Counter(item_by_id[item_id].popularity_tier for item_id in candidate_ids)
        tier_gu = group_unfairness(
            {str(key): float(value) for key, value in rec_tiers.items()},
            {str(key): float(value) for key, value in ref_tiers.items()},
        )

        def genre_counts(item_ids: list[str] | set[str]) -> Counter[str]:
            result: Counter[str] = Counter()
            for item_id in item_ids:
                result.update(item_by_id[item_id].genres or ["unknown"])
            return result

        genre_gu = group_unfairness(genre_counts(recommended), genre_counts(candidate_ids))
        rows.append(
            {
                **dict(zip(condition_columns, condition, strict=True)),
                "gini": gini_index(vector),
                "hhi": hhi(vector),
                "arp": average_recommendation_popularity(recommended, popularity),
                "catalog_coverage": catalog_coverage(recommended, catalog_ids),
                "long_tail_coverage": long_tail_coverage(recommended, tail_ids),
                "popularity_mgu": mgu(tier_gu),
                "popularity_dgu": dgu(tier_gu),
                "genre_mgu": mgu(genre_gu),
                "genre_dgu": dgu(genre_gu),
                "total_exposure": sum(vector),
            }
        )
    return pd.DataFrame(rows)


def compute_condition_opportunity_metrics(
    queries: pd.DataFrame, catalog: list[Item], *, k: int
) -> pd.DataFrame:
    """Measure exposure concentration after conditioning on item eligibility per query."""
    condition_columns = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    item_by_id = {item.item_id: item for item in catalog}
    rows: list[dict[str, object]] = []
    for condition, group in queries.groupby(condition_columns, dropna=False):
        opportunity_counts: Counter[str] = Counter()
        exposure_counts_by_item: Counter[str] = Counter()
        for record in group.to_dict(orient="records"):
            candidates = [str(item_id) for item_id in record["candidate_item_ids"]]
            if len(candidates) != len(set(candidates)):
                raise ValueError(
                    f"Candidate pool contains duplicate items for {record['query_id']}"
                )
            recommended = [str(item_id) for item_id in record["matched_item_ids"][:k]]
            if not set(recommended).issubset(candidates):
                raise ValueError("Within-opportunity analysis requires grounded recommendations")
            opportunity_counts.update(candidates)
            exposure_counts_by_item.update(recommended)
        item_ids = sorted(opportunity_counts)
        missing = set(item_ids) - set(item_by_id)
        if missing:
            raise KeyError(f"Candidate items missing from catalog: {sorted(missing)[:5]}")
        exposure_values = np.asarray(
            [exposure_counts_by_item[item_id] for item_id in item_ids], dtype=float
        )
        opportunity_values = np.asarray(
            [opportunity_counts[item_id] for item_id in item_ids], dtype=float
        )
        tail_mask = np.asarray(
            [item_by_id[item_id].popularity_tier == "tail" for item_id in item_ids],
            dtype=bool,
        )
        tail_coverage = (
            within_opportunity_coverage(
                exposure_values[tail_mask].tolist(), opportunity_values[tail_mask].tolist()
            )
            if tail_mask.any()
            else np.nan
        )
        rows.append(
            {
                **dict(zip(condition_columns, condition, strict=True)),
                "opportunity_gini": opportunity_adjusted_gini(
                    exposure_values.tolist(), opportunity_values.tolist()
                ),
                "opportunity_hhi": opportunity_adjusted_hhi(
                    exposure_values.tolist(), opportunity_values.tolist()
                ),
                "opportunity_normalized_hhi": opportunity_adjusted_normalized_hhi(
                    exposure_values.tolist(), opportunity_values.tolist()
                ),
                "opportunity_coverage": within_opportunity_coverage(
                    exposure_values.tolist(), opportunity_values.tolist()
                ),
                "opportunity_long_tail_coverage": tail_coverage,
                "eligible_item_count": len(item_ids),
                "candidate_opportunities": float(opportunity_values.sum()),
                "total_exposure": float(exposure_values.sum()),
                "overall_selection_rate": float(exposure_values.sum() / opportunity_values.sum()),
            }
        )
    return pd.DataFrame(rows)


def opportunity_metric_deltas(opportunity_metrics: pd.DataFrame) -> pd.DataFrame:
    """Compute within-opportunity sensitive-minus-neutral condition differences."""
    family = ["model", "domain", "phrasing_variant"]
    neutral = opportunity_metrics.loc[
        (opportunity_metrics["trait"] == "neutral")
        & (opportunity_metrics["trait_level"] == "neutral"),
        [*family, *OPPORTUNITY_METRIC_COLUMNS],
    ].rename(columns={metric: f"neutral_{metric}" for metric in OPPORTUNITY_METRIC_COLUMNS})
    sensitive = opportunity_metrics.loc[opportunity_metrics["trait_level"] != "neutral"].copy()
    merged = sensitive.merge(neutral, on=family, how="left", validate="many_to_one")
    for metric in OPPORTUNITY_METRIC_COLUMNS:
        merged[f"delta_{metric}"] = merged[metric] - merged[f"neutral_{metric}"]
    return merged


def load_paired_analysis_queries(path: str | Path) -> pd.DataFrame:
    """Reconstruct a complete selected query view from a frozen paired-analysis table."""
    columns = [
        "query_id",
        "persona_id",
        "model",
        "domain",
        "trait",
        "trait_level",
        "phrasing_variant",
        "repeat_idx",
        "candidate_item_ids",
        "matched_item_ids",
        "neutral_items",
    ]
    paired = pd.read_csv(path, usecols=columns, dtype=str, keep_default_na=False)
    pair_keys = ["persona_id", "model", "domain", "phrasing_variant", "repeat_idx"]
    for field in ("candidate_item_ids", "neutral_items"):
        inconsistent = paired.groupby(pair_keys, dropna=False)[field].nunique().gt(1)
        if inconsistent.any():
            raise ValueError(f"Paired analysis has inconsistent {field} within neutral pair")

    def item_ids(value: str) -> list[str]:
        return _QUOTED_ITEM_ID.findall(value)

    sensitive = paired.drop(columns="neutral_items").copy()
    sensitive["candidate_item_ids"] = sensitive["candidate_item_ids"].map(item_ids)
    sensitive["matched_item_ids"] = sensitive["matched_item_ids"].map(item_ids)

    neutral = paired.drop_duplicates(pair_keys).copy()
    neutral["query_id"] = (
        neutral[pair_keys]
        .agg("|".join, axis=1)
        .map(lambda value: hashlib.sha256(f"neutral|{value}".encode()).hexdigest()[:24])
    )
    neutral["trait"] = "neutral"
    neutral["trait_level"] = "neutral"
    neutral["candidate_item_ids"] = neutral["candidate_item_ids"].map(item_ids)
    neutral["matched_item_ids"] = neutral["neutral_items"].map(item_ids)
    neutral = neutral.drop(columns="neutral_items")
    reconstructed = pd.concat([sensitive, neutral], ignore_index=True)
    reconstructed["repeat_idx"] = reconstructed["repeat_idx"].astype(int)
    if reconstructed["query_id"].duplicated().any():
        raise ValueError("Reconstructed paired query view contains duplicate query IDs")
    return reconstructed


def item_metric_deltas(item_metrics: pd.DataFrame) -> pd.DataFrame:
    """Compute each personality condition's change from its matched neutral baseline."""
    family = ["model", "domain", "phrasing_variant"]
    metric_columns = [
        "gini",
        "hhi",
        "arp",
        "catalog_coverage",
        "long_tail_coverage",
        "popularity_mgu",
        "popularity_dgu",
        "genre_mgu",
        "genre_dgu",
    ]
    neutral = item_metrics.loc[
        (item_metrics["trait"] == "neutral") & (item_metrics["trait_level"] == "neutral"),
        [*family, *metric_columns],
    ].rename(columns={metric: f"neutral_{metric}" for metric in metric_columns})
    sensitive = item_metrics.loc[item_metrics["trait_level"] != "neutral"].copy()
    merged = sensitive.merge(neutral, on=family, how="left", validate="many_to_one")
    for metric in metric_columns:
        merged[f"delta_{metric}"] = merged[metric] - merged[f"neutral_{metric}"]
    return merged


def group_exposure_diagnostics(
    queries: pd.DataFrame, catalog: list[Item], *, k: int
) -> pd.DataFrame:
    """Expose the popularity/genre/provider proportions underlying MGU and DGU."""
    conditions = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    item_by_id = {item.item_id: item for item in catalog}
    rows: list[dict[str, object]] = []

    def labels(item: Item, group_type: str) -> list[str]:
        if group_type == "popularity_tier":
            return [item.popularity_tier]
        if group_type == "genre":
            return item.genres or ["unknown"]
        return [item.provider_or_studio or "unknown"]

    for condition, group in queries.groupby(conditions, dropna=False):
        recommended = [item_id for values in group["matched_item_ids"] for item_id in values[:k]]
        candidates = list({item_id for values in group["candidate_item_ids"] for item_id in values})
        prefix = dict(zip(conditions, condition, strict=True))
        for group_type in ("popularity_tier", "genre", "provider"):
            rec_counts: Counter[str] = Counter()
            ref_counts: Counter[str] = Counter()
            for item_id in recommended:
                rec_counts.update(labels(item_by_id[item_id], group_type))
            for item_id in candidates:
                ref_counts.update(labels(item_by_id[item_id], group_type))
            if not rec_counts or not ref_counts:
                continue
            unfairness = group_unfairness(rec_counts, ref_counts)
            rec_total, ref_total = sum(rec_counts.values()), sum(ref_counts.values())
            for group_name in sorted(set(rec_counts) | set(ref_counts)):
                rows.append(
                    {
                        **prefix,
                        "group_type": group_type,
                        "group": group_name,
                        "recommendation_share": rec_counts[group_name] / rec_total,
                        "reference_share": ref_counts[group_name] / ref_total,
                        "group_unfairness": unfairness[group_name],
                    }
                )
    return pd.DataFrame(rows)


def summarize_user_side(paired: pd.DataFrame) -> pd.DataFrame:
    """Average individual similarities per condition and add FairEval family summaries."""
    condition = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    means = (
        paired.groupby(condition, dropna=False)[["jaccard", "serp", "prag"]].mean().reset_index()
    )
    family = ["model", "domain", "phrasing_variant"]
    rows: list[dict[str, object]] = []
    for keys, group in paired.groupby(family, dropna=False):
        prefix = dict(zip(family, keys, strict=True))
        for metric in ("jaccard", "serp", "prag"):
            level_means = group.groupby("trait_level")[metric].mean().to_numpy(dtype=float)
            values = group[metric].to_numpy(dtype=float)
            rows.append(
                {
                    **prefix,
                    "similarity_metric": metric,
                    "snsr": float(level_means.max() - level_means.min()),
                    "snsv": float(level_means.std(ddof=0)),
                    "pafs": float(1 - np.mean(np.abs(values - values.mean()))),
                }
            )
    summaries = pd.DataFrame(rows)
    wide = summaries.pivot(
        index=family,
        columns="similarity_metric",
        values=["snsr", "snsv", "pafs"],
    )
    flat_columns = cast(list[tuple[str, str]], wide.columns.tolist())
    wide.columns = [f"{left}_{right}" for left, right in flat_columns]
    return means.merge(wide.reset_index(), on=family, how="left")


def reground_queries(
    queries: pd.DataFrame,
    catalog: list[Item],
    *,
    fuzzy_threshold: float,
    ambiguity_margin: float,
) -> pd.DataFrame:
    """Reparse immutable raw text so matcher fixes never require another model call."""
    required = {"raw_response_text", "candidate_item_ids"}
    missing = required - set(queries.columns)
    if missing:
        raise ValueError(f"Cannot re-ground queries; missing columns: {sorted(missing)}")
    result = queries.copy()
    title_matcher = TitleMatcher(catalog)
    for index, row in result.iterrows():
        parsed = parse_response(str(row["raw_response_text"]))
        matched = title_matcher.match(
            parsed,
            allowed_item_ids=frozenset(str(value) for value in row["candidate_item_ids"]),
            threshold=fuzzy_threshold,
            ambiguity_margin=ambiguity_margin,
        )
        result.at[index, "parsed_titles"] = parsed
        result.at[index, "matched_item_ids"] = matched.matched_item_ids
        result.at[index, "hallucinated_titles"] = matched.hallucinated_titles
        result.at[index, "off_list_titles"] = matched.off_list_titles
    result["grounding_version"] = "allowed-title-annotation-v3"
    return result


def select_analysis_view(queries: pd.DataFrame, *, view: AnalysisView, k: int) -> pd.DataFrame:
    """Return a preregistered derived view without mutating immutable query records."""
    if view == "primary":
        selected = queries
    elif view == "exact-10-grounded":
        selected = queries.loc[queries["matched_item_ids"].map(len).eq(k)]
    elif view == "exclude-flagged-records":
        no_hallucinations = queries["hallucinated_titles"].map(len).eq(0)
        no_off_list = queries["off_list_titles"].map(len).eq(0)
        selected = queries.loc[no_hallucinations & no_off_list]
    else:
        raise ValueError(f"Unknown analysis view: {view}")
    if view != "primary":
        pair_keys = ["persona_id", "model", "domain", "phrasing_variant", "repeat_idx"]
        missing = set(pair_keys) - set(selected.columns)
        if missing:
            raise ValueError(f"Sensitivity view cannot verify neutral pairs: {sorted(missing)}")
        neutral_keys = (
            selected.loc[selected["trait_level"].eq("neutral"), pair_keys]
            .drop_duplicates()
            .assign(__neutral_pair=True)
        )
        selected = selected.merge(
            neutral_keys,
            on=pair_keys,
            how="inner",
            validate="many_to_one",
        ).drop(columns="__neutral_pair")
    return selected.reset_index(drop=True)


def relevance_table(queries: pd.DataFrame, *, k: int) -> pd.DataFrame:
    """Compute query-level utility controls from independently fixed relevance labels."""
    columns = [
        "query_id",
        "persona_id",
        "model",
        "domain",
        "trait",
        "trait_level",
        "phrasing_variant",
        "repeat_idx",
    ]
    if "relevant_item_ids" not in queries:
        result = queries[columns].copy()
        result["precision_at_k"] = np.nan
        result["ndcg_at_k"] = np.nan
        result["relevance_labels_available"] = False
        return result
    rows: list[dict[str, object]] = []
    for record in queries.to_dict(orient="records"):
        relevant = set(record["relevant_item_ids"])
        available = bool(relevant)
        rows.append(
            {
                **{column: record[column] for column in columns},
                "precision_at_k": (
                    precision_at_k(record["matched_item_ids"], relevant, k) if available else np.nan
                ),
                "ndcg_at_k": (
                    ndcg_at_k(record["matched_item_ids"], relevant, k) if available else np.nan
                ),
                "relevance_labels_available": available,
            }
        )
    return pd.DataFrame(rows)


def per_query_item_outcomes(queries: pd.DataFrame, catalog: list[Item], *, k: int) -> pd.DataFrame:
    """Derive persona-level item outcomes suitable for mixed-effects inference."""
    item_by_id = {item.item_id: item for item in catalog}
    rows: list[dict[str, object]] = []
    identity = [
        "query_id",
        "persona_id",
        "model",
        "domain",
        "trait",
        "trait_level",
        "phrasing_variant",
        "repeat_idx",
    ]
    for record in queries.to_dict(orient="records"):
        items = [item_by_id[item_id] for item_id in record["matched_item_ids"][:k]]
        size = len(items)
        rows.append(
            {
                **{column: record[column] for column in identity},
                "query_arp": (
                    float(
                        np.mean(
                            [item.interaction_count or 1 / item.popularity_rank for item in items]
                        )
                    )
                    if items
                    else np.nan
                ),
                "head_share": sum(item.popularity_tier == "head" for item in items) / size
                if size
                else np.nan,
                "tail_share": sum(item.popularity_tier == "tail" for item in items) / size
                if size
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def mixed_effects_tables(
    paired: pd.DataFrame, query_item_outcomes: pd.DataFrame, *, alpha: float
) -> pd.DataFrame:
    """Fit pre-registered persona-random-intercept models and tabulate coefficients."""
    user = paired.copy()
    for metric in ("jaccard", "serp", "prag"):
        user[f"{metric}_harm"] = 1 - user[metric]
    datasets = [
        (user, ("jaccard_harm", "serp_harm", "prag_harm"), "user_side"),
        (query_item_outcomes, ("query_arp", "head_share", "tail_share"), "item_side"),
    ]
    rows: list[dict[str, object]] = []
    candidate_effects = ("trait", "trait_level", "phrasing_variant", "model")
    for data, outcomes, family in datasets:
        fixed_effects = tuple(
            effect for effect in candidate_effects if data[effect].nunique(dropna=True) > 1
        )
        for outcome in outcomes:
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    result = fit_mixed_effects(
                        data,
                        outcome=outcome,
                        fixed_effects=fixed_effects,
                    )
                warning_text = " | ".join(dict.fromkeys(str(item.message) for item in caught))
                for term in result.params.index:
                    rows.append(
                        {
                            "metric_family": family,
                            "outcome": outcome,
                            "term": term,
                            "coefficient": float(result.params[term]),
                            "standard_error": float(result.bse[term]),
                            "p_value": float(result.pvalues[term]),
                            "converged": bool(result.converged),
                            "warnings": warning_text,
                        }
                    )
            except Exception as error:  # statsmodels failures must be reportable, never silent
                rows.append(
                    {
                        "metric_family": family,
                        "outcome": outcome,
                        "term": "__model_failure__",
                        "note": f"{type(error).__name__}: {error}",
                        "converged": False,
                    }
                )
    table = pd.DataFrame(rows)
    if "p_value" not in table:
        table["p_value"] = np.nan
    valid = table["p_value"].notna()
    table["p_value_bh"] = np.nan
    table["reject_bh"] = False
    if valid.any():
        rejected, adjusted = benjamini_hochberg(
            table.loc[valid, "p_value"].to_numpy(dtype=float), alpha=alpha
        )
        table.loc[valid, "p_value_bh"] = adjusted
        table.loc[valid, "reject_bh"] = rejected
    return table


def rq3_correlation_table(
    user_metrics: pd.DataFrame,
    item_metrics: pd.DataFrame,
    *,
    alpha: float,
    minimum_effect: float,
) -> pd.DataFrame:
    """Compare condition rankings after explicitly orienting all metrics as harm."""
    keys = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    merged = user_metrics.merge(item_metrics, on=keys, validate="one_to_one")
    item_harm = {
        "gini": 1.0,
        "hhi": 1.0,
        "arp": 1.0,
        "catalog_coverage": -1.0,
        "long_tail_coverage": -1.0,
        "popularity_mgu": 1.0,
        "popularity_dgu": 1.0,
        "genre_mgu": 1.0,
        "genre_dgu": 1.0,
    }
    rows: list[dict[str, object]] = []
    for (model, domain), group in merged.groupby(["model", "domain"], dropna=False):
        for user_metric in ("jaccard", "serp", "prag"):
            for item_metric, direction in item_harm.items():
                try:
                    result = spearman_fairness_scenario(
                        1 - group[user_metric].to_numpy(dtype=float),
                        direction * group[item_metric].to_numpy(dtype=float),
                        alpha=alpha,
                        minimum_effect=minimum_effect,
                    )
                    row = {
                        "model": model,
                        "domain": domain,
                        "user_metric": user_metric,
                        "item_metric": item_metric,
                        "rho": result.rho,
                        "p_value": result.p_value,
                        "scenario": result.scenario,
                    }
                except ValueError as error:
                    row = {
                        "model": model,
                        "domain": domain,
                        "user_metric": user_metric,
                        "item_metric": item_metric,
                        "rho": np.nan,
                        "p_value": np.nan,
                        "scenario": "undefined",
                        "note": str(error),
                    }
                rows.append(row)
    table = pd.DataFrame(rows)
    valid = table["p_value"].notna()
    table["p_value_bh"] = np.nan
    table["reject_bh"] = False
    if valid.any():
        rejected, adjusted = benjamini_hochberg(
            table.loc[valid, "p_value"].to_numpy(dtype=float), alpha=alpha
        )
        table.loc[valid, "p_value_bh"] = adjusted
        table.loc[valid, "reject_bh"] = rejected
    return table


def bootstrap_condition_item_metrics(
    queries: pd.DataFrame,
    catalog: list[Item],
    *,
    k: int,
    n_resamples: int,
    confidence_level: float,
    seed: int,
) -> pd.DataFrame:
    """Efficient persona bootstrap over sparse catalog exposure vectors."""
    condition_columns = ["model", "domain", "trait", "trait_level", "phrasing_variant"]
    catalog_size = len(catalog)
    popularity = {
        item.item_id: float(item.interaction_count or (1 / item.popularity_rank))
        for item in catalog
    }
    alpha = 1 - confidence_level
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []

    def sparse_gini(counts: np.ndarray) -> float:
        positive = np.sort(counts[counts > 0])
        if positive.size == 0:
            return 0.0
        ranks = np.arange(catalog_size - positive.size + 1, catalog_size + 1)
        return float(
            2 * np.dot(ranks, positive) / (catalog_size * positive.sum())
            - (catalog_size + 1) / catalog_size
        )

    for condition, group in queries.groupby(condition_columns, dropna=False):
        item_ids = sorted({item for values in group["matched_item_ids"] for item in values[:k]})
        item_index = {item_id: index for index, item_id in enumerate(item_ids)}
        personas = group["persona_id"].drop_duplicates().tolist()
        matrix = np.zeros((len(personas), len(item_ids)), dtype=float)
        for persona_index, persona in enumerate(personas):
            for values in group.loc[group["persona_id"] == persona, "matched_item_ids"]:
                for item_id in values[:k]:
                    matrix[persona_index, item_index[item_id]] += 1
        pop_vector = np.asarray([popularity[item_id] for item_id in item_ids], dtype=float)
        replicates: dict[str, list[float]] = {"gini": [], "hhi": [], "arp": []}
        for _ in range(n_resamples):
            draw = rng.integers(0, len(personas), size=len(personas))
            counts = matrix[draw].sum(axis=0)
            total = counts.sum()
            replicates["gini"].append(sparse_gini(counts))
            replicates["hhi"].append(float(np.square(counts / total).sum()) if total else 0.0)
            replicates["arp"].append(float(np.dot(counts, pop_vector) / total) if total else np.nan)
        prefix = dict(zip(condition_columns, condition, strict=True))
        for metric, values in replicates.items():
            array = np.asarray(values, dtype=float)
            lower, upper = np.nanquantile(array, [alpha / 2, 1 - alpha / 2])
            rows.append(
                {
                    **prefix,
                    "metric": metric,
                    "ci_lower": float(lower),
                    "ci_upper": float(upper),
                    "confidence_level": confidence_level,
                    "n_resamples": n_resamples,
                }
            )
    return pd.DataFrame(rows)


def bootstrap_item_metric_deltas(
    queries: pd.DataFrame,
    catalog: list[Item],
    *,
    k: int,
    n_resamples: int,
    confidence_level: float,
    seed: int,
) -> pd.DataFrame:
    """Paired persona bootstrap CIs for sensitive-minus-neutral aggregate shifts."""
    # Neutral rows use trait="neutral", so trait cannot be part of the family key;
    # otherwise every sensitive-trait group has an empty neutral baseline.
    family = ["model", "domain", "phrasing_variant"]
    catalog_size = len(catalog)
    popularity = {
        item.item_id: float(item.interaction_count or (1 / item.popularity_rank))
        for item in catalog
    }
    alpha = 1 - confidence_level
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []

    def sparse_metrics(counts: np.ndarray, pop_vector: np.ndarray) -> dict[str, float]:
        total = counts.sum()
        if total == 0:
            return {"gini": 0.0, "hhi": 0.0, "arp": np.nan}
        positive = np.sort(counts[counts > 0])
        ranks = np.arange(catalog_size - positive.size + 1, catalog_size + 1)
        gini = float(
            2 * np.dot(ranks, positive) / (catalog_size * positive.sum())
            - (catalog_size + 1) / catalog_size
        )
        return {
            "gini": gini,
            "hhi": float(np.square(counts / total).sum()),
            "arp": float(np.dot(counts, pop_vector) / total),
        }

    for keys, group in queries.groupby(family, dropna=False):
        neutral = group.loc[(group["trait"] == "neutral") & (group["trait_level"] == "neutral")]
        sensitive_conditions = group.loc[group["trait_level"] != "neutral"].groupby(
            ["trait", "trait_level"], dropna=False
        )
        for (trait, level), sensitive in sensitive_conditions:
            personas = sorted(set(neutral["persona_id"]) & set(sensitive["persona_id"]))
            if not personas:
                continue
            item_ids = sorted(
                {
                    item_id
                    for frame in (neutral, sensitive)
                    for values in frame["matched_item_ids"]
                    for item_id in values[:k]
                }
            )
            item_index = {item_id: index for index, item_id in enumerate(item_ids)}
            matrices: list[np.ndarray] = []
            for frame in (neutral, sensitive):
                matrix = np.zeros((len(personas), len(item_ids)), dtype=float)
                for persona_index, persona in enumerate(personas):
                    for values in frame.loc[frame["persona_id"] == persona, "matched_item_ids"]:
                        for item_id in values[:k]:
                            matrix[persona_index, item_index[item_id]] += 1
                matrices.append(matrix)
            pop_vector = np.asarray([popularity[item_id] for item_id in item_ids], dtype=float)
            replicates: dict[str, list[float]] = {"gini": [], "hhi": [], "arp": []}
            for _ in range(n_resamples):
                draw = rng.integers(0, len(personas), size=len(personas))
                baseline_metrics = sparse_metrics(matrices[0][draw].sum(axis=0), pop_vector)
                sensitive_metrics = sparse_metrics(matrices[1][draw].sum(axis=0), pop_vector)
                for metric in replicates:
                    replicates[metric].append(sensitive_metrics[metric] - baseline_metrics[metric])
            prefix = {
                **dict(zip(family, keys, strict=True)),
                "trait": trait,
                "trait_level": level,
            }
            for metric, values in replicates.items():
                array = np.asarray(values, dtype=float)
                lower, upper = np.nanquantile(array, [alpha / 2, 1 - alpha / 2])
                rows.append(
                    {
                        **prefix,
                        "metric": metric,
                        "delta_ci_lower": float(lower),
                        "delta_ci_upper": float(upper),
                        "confidence_level": confidence_level,
                        "n_resamples": n_resamples,
                    }
                )
    return pd.DataFrame(rows)


def _persona_opportunity_matrices(
    frame: pd.DataFrame,
    personas: list[str],
    item_index: dict[str, int],
    *,
    k: int,
) -> tuple[np.ndarray, np.ndarray]:
    persona_index = {persona: index for index, persona in enumerate(personas)}
    exposure = np.zeros((len(personas), len(item_index)), dtype=float)
    opportunity = np.zeros_like(exposure)
    for record in frame.to_dict(orient="records"):
        persona = str(record["persona_id"])
        if persona not in persona_index:
            continue
        row = persona_index[persona]
        candidates = [str(item_id) for item_id in record["candidate_item_ids"]]
        recommended = [str(item_id) for item_id in record["matched_item_ids"][:k]]
        if not set(recommended).issubset(candidates):
            raise ValueError("Within-opportunity analysis requires grounded recommendations")
        for item_id in candidates:
            opportunity[row, item_index[item_id]] += 1
        for item_id in recommended:
            exposure[row, item_index[item_id]] += 1
    return exposure, opportunity


def _opportunity_metrics_from_arrays(
    exposure: np.ndarray, opportunity: np.ndarray, tail_mask: np.ndarray
) -> dict[str, float]:
    eligible = opportunity > 0
    if not eligible.any():
        raise ValueError("Bootstrap replicate has no candidate opportunity")
    tail_eligible = eligible & tail_mask
    return {
        "opportunity_gini": opportunity_adjusted_gini(
            exposure[eligible].tolist(), opportunity[eligible].tolist()
        ),
        "opportunity_hhi": opportunity_adjusted_hhi(
            exposure[eligible].tolist(), opportunity[eligible].tolist()
        ),
        "opportunity_normalized_hhi": opportunity_adjusted_normalized_hhi(
            exposure[eligible].tolist(), opportunity[eligible].tolist()
        ),
        "opportunity_coverage": within_opportunity_coverage(
            exposure[eligible].tolist(), opportunity[eligible].tolist()
        ),
        "opportunity_long_tail_coverage": (
            within_opportunity_coverage(
                exposure[tail_eligible].tolist(), opportunity[tail_eligible].tolist()
            )
            if tail_eligible.any()
            else np.nan
        ),
    }


def _opportunity_metrics_from_matrix(
    exposure: np.ndarray, opportunity: np.ndarray, tail_mask: np.ndarray
) -> dict[str, np.ndarray]:
    """Vectorized counterpart used only to accelerate persona-bootstrap replicates."""
    eligible = opportunity > 0
    eligible_count = eligible.sum(axis=1)
    if np.any(eligible_count == 0):
        raise ValueError("Bootstrap replicate has no candidate opportunity")
    rates = np.zeros_like(exposure, dtype=float)
    np.divide(exposure, opportunity, out=rates, where=eligible)
    rate_total = rates.sum(axis=1)
    raw_hhi = np.divide(
        np.square(rates).sum(axis=1),
        np.square(rate_total),
        out=np.zeros_like(rate_total),
        where=rate_total > 0,
    )
    normalized = np.zeros_like(raw_hhi)
    multiple = eligible_count > 1
    normalized[multiple] = (raw_hhi[multiple] - 1 / eligible_count[multiple]) / (
        1 - 1 / eligible_count[multiple]
    )
    normalized[~multiple & (rate_total > 0)] = 1.0

    sortable = np.where(eligible, rates, np.inf)
    sorted_rates = np.sort(sortable, axis=1)
    sorted_rates[~np.isfinite(sorted_rates)] = 0.0
    positions = np.arange(1, rates.shape[1] + 1, dtype=float)
    valid_position = positions[None, :] <= eligible_count[:, None]
    weighted_sum = (sorted_rates * positions[None, :] * valid_position).sum(axis=1)
    gini = (
        np.divide(
            2 * weighted_sum,
            eligible_count * rate_total,
            out=np.zeros_like(rate_total),
            where=rate_total > 0,
        )
        - (eligible_count + 1) / eligible_count
    )
    gini[rate_total == 0] = 0.0

    tail_eligible = eligible & tail_mask[None, :]
    tail_denominator = tail_eligible.sum(axis=1)
    tail_coverage = np.divide(
        ((exposure > 0) & tail_eligible).sum(axis=1),
        tail_denominator,
        out=np.full(exposure.shape[0], np.nan, dtype=float),
        where=tail_denominator > 0,
    )
    return {
        "opportunity_gini": gini,
        "opportunity_hhi": raw_hhi,
        "opportunity_normalized_hhi": normalized,
        "opportunity_coverage": ((exposure > 0) & eligible).sum(axis=1) / eligible_count,
        "opportunity_long_tail_coverage": tail_coverage,
    }


def bootstrap_opportunity_metric_deltas(
    queries: pd.DataFrame,
    catalog: list[Item],
    *,
    k: int,
    n_resamples: int,
    confidence_level: float,
    seed: int,
) -> pd.DataFrame:
    """Paired persona-bootstrap CIs for opportunity-adjusted sensitive-minus-neutral shifts."""
    if n_resamples < 1:
        raise ValueError("Opportunity bootstrap needs at least one resample")
    family = ["model", "domain", "phrasing_variant"]
    pair_keys = ["persona_id", "repeat_idx"]
    item_by_id = {item.item_id: item for item in catalog}
    alpha = 1 - confidence_level
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for keys, group in queries.groupby(family, dropna=False):
        neutral = group.loc[(group["trait"] == "neutral") & (group["trait_level"] == "neutral")]
        sensitive_conditions = group.loc[group["trait_level"] != "neutral"].groupby(
            ["trait", "trait_level"], dropna=False
        )
        for (trait, level), sensitive in sensitive_conditions:
            pairs = sensitive[pair_keys].drop_duplicates()
            paired_neutral = neutral.merge(
                pairs,
                on=pair_keys,
                how="inner",
                validate="one_to_one",
            )
            personas = sorted(
                set(paired_neutral["persona_id"].astype(str))
                & set(sensitive["persona_id"].astype(str))
            )
            if not personas:
                continue
            item_ids = sorted(
                {
                    str(item_id)
                    for frame in (paired_neutral, sensitive)
                    for values in frame["candidate_item_ids"]
                    for item_id in values
                }
            )
            missing = set(item_ids) - set(item_by_id)
            if missing:
                raise KeyError(f"Candidate items missing from catalog: {sorted(missing)[:5]}")
            item_index = {item_id: index for index, item_id in enumerate(item_ids)}
            tail_mask = np.asarray(
                [item_by_id[item_id].popularity_tier == "tail" for item_id in item_ids],
                dtype=bool,
            )
            baseline = _persona_opportunity_matrices(paired_neutral, personas, item_index, k=k)
            conditioned = _persona_opportunity_matrices(sensitive, personas, item_index, k=k)
            replicates: dict[str, list[float]] = {
                metric: [] for metric in OPPORTUNITY_METRIC_COLUMNS
            }
            batch_size = min(100, n_resamples)
            probabilities = np.full(len(personas), 1 / len(personas), dtype=float)
            for start in range(0, n_resamples, batch_size):
                size = min(batch_size, n_resamples - start)
                weights = rng.multinomial(len(personas), probabilities, size=size)
                baseline_metrics = _opportunity_metrics_from_matrix(
                    weights @ baseline[0], weights @ baseline[1], tail_mask
                )
                conditioned_metrics = _opportunity_metrics_from_matrix(
                    weights @ conditioned[0], weights @ conditioned[1], tail_mask
                )
                for metric in OPPORTUNITY_METRIC_COLUMNS:
                    replicates[metric].extend(
                        (conditioned_metrics[metric] - baseline_metrics[metric]).tolist()
                    )
            prefix = {
                **dict(zip(family, keys, strict=True)),
                "trait": trait,
                "trait_level": level,
            }
            for metric, values in replicates.items():
                array = np.asarray(values, dtype=float)
                lower, upper = np.nanquantile(array, [alpha / 2, 1 - alpha / 2])
                rows.append(
                    {
                        **prefix,
                        "metric": metric,
                        "delta_ci_lower": float(lower),
                        "delta_ci_upper": float(upper),
                        "confidence_level": confidence_level,
                        "n_resamples": n_resamples,
                    }
                )
    return pd.DataFrame(rows)


def write_analysis_outputs(
    queries: pd.DataFrame,
    catalog: list[Item],
    *,
    k: int,
    table_dir: str | Path,
    bootstrap_resamples: int = 2_000,
    confidence_level: float = 0.95,
    seed: int = 0,
    alpha: float = 0.05,
    rq3_minimum_effect: float = 0.20,
    opportunity_bootstrap_resamples: int | None = None,
) -> dict[str, Path]:
    destination = Path(table_dir)
    destination.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}
    paired = paired_similarities(queries, k=k)
    user_metrics = summarize_user_side(paired)
    item_metrics = compute_condition_item_metrics(queries, catalog, k=k)
    item_deltas = item_metric_deltas(item_metrics)
    opportunity_metrics = compute_condition_opportunity_metrics(queries, catalog, k=k)
    opportunity_deltas = opportunity_metric_deltas(opportunity_metrics)
    query_item_outcomes = per_query_item_outcomes(queries, catalog, k=k)
    tables = {
        "condition_diagnostics": condition_diagnostics(queries),
        "user_side_similarities": paired,
        "user_side_metrics": user_metrics,
        "relevance_metrics": relevance_table(queries, k=k),
        "per_query_item_outcomes": query_item_outcomes,
        "item_side_metrics": item_metrics,
        "item_side_deltas": item_deltas,
        "opportunity_adjusted_metrics": opportunity_metrics,
        "opportunity_adjusted_deltas": opportunity_deltas,
        "group_exposure_diagnostics": group_exposure_diagnostics(queries, catalog, k=k),
        "item_side_bootstrap_cis": bootstrap_condition_item_metrics(
            queries,
            catalog,
            k=k,
            n_resamples=bootstrap_resamples,
            confidence_level=confidence_level,
            seed=seed,
        ),
        "item_side_delta_bootstrap_cis": bootstrap_item_metric_deltas(
            queries,
            catalog,
            k=k,
            n_resamples=bootstrap_resamples,
            confidence_level=confidence_level,
            seed=seed,
        ),
        "opportunity_adjusted_delta_bootstrap_cis": bootstrap_opportunity_metric_deltas(
            queries,
            catalog,
            k=k,
            n_resamples=opportunity_bootstrap_resamples or bootstrap_resamples,
            confidence_level=confidence_level,
            seed=seed,
        ),
        "rq3_correlations": rq3_correlation_table(
            user_metrics,
            item_metrics,
            alpha=alpha,
            minimum_effect=rq3_minimum_effect,
        ),
        "mixed_effects": mixed_effects_tables(paired, query_item_outcomes, alpha=alpha),
    }
    for name, frame in tables.items():
        path = destination / f"{name}.csv"
        frame.to_csv(path, index=False)
        outputs[name] = path
    return outputs


def pilot_cost_projection(queries: pd.DataFrame, full_query_count: int) -> dict[str, float]:
    unique_paid_calls = queries.loc[(queries["prompt_tokens"] + queries["completion_tokens"]) > 0]
    average = float(unique_paid_calls["cost_usd"].mean()) if len(unique_paid_calls) else 0.0
    return {
        "pilot_unique_calls": len(unique_paid_calls),
        "average_cost_per_unique_call_usd": average,
        "projected_full_unique_calls": int(full_query_count),
        "projected_full_cost_usd": average * full_query_count,
    }


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
