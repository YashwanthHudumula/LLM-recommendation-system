"""Deterministic fixed candidate pools for anti-hallucination prompting."""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection
from dataclasses import dataclass

import numpy as np

from recllm_fairness.data.catalog import Item


@dataclass(frozen=True)
class CandidatePool:
    items: tuple[Item, ...]

    @property
    def item_ids(self) -> frozenset[str]:
        return frozenset(item.item_id for item in self.items)

    def prompt_block(self) -> str:
        return "\n".join(f"C{index:03d} | {item.title}" for index, item in enumerate(self.items, 1))


def build_candidate_pool(
    catalog: list[Item],
    *,
    size: int,
    head_fraction: float,
    mid_fraction: float,
    tail_fraction: float,
    seed: int,
    required_item_ids: Collection[str] = (),
    minimum_required: int = 0,
    shuffle_items: bool = False,
) -> CandidatePool:
    """Build a reproducible tier-stratified pool with optional relevance opportunity."""
    if not catalog or size < 1:
        raise ValueError("Candidate pool needs a non-empty catalog and positive size")
    fractions = (head_fraction, mid_fraction, tail_fraction)
    if any(value < 0 for value in fractions) or not np.isclose(sum(fractions), 1.0):
        raise ValueError("Candidate fractions must be non-negative and sum to one")
    size = min(size, len(catalog))
    raw = np.array(fractions) * size
    allocations = np.floor(raw).astype(int)
    for index in np.argsort(-(raw - allocations))[: size - int(allocations.sum())]:
        allocations[index] += 1

    by_tier = {
        tier: sorted(
            (item for item in catalog if item.popularity_tier == tier),
            key=lambda item: (item.popularity_rank, item.item_id),
        )
        for tier in ("head", "mid", "tail")
    }
    rng = np.random.default_rng(seed)
    chosen: list[Item] = []
    required_ids = set(required_item_ids)
    required_catalog = [item for item in catalog if item.item_id in required_ids]
    required_target = min(minimum_required, len(required_catalog), size)
    if minimum_required < 0:
        raise ValueError("minimum_required must be non-negative")
    if required_target:
        required_pool = build_candidate_pool(
            required_catalog,
            size=required_target,
            head_fraction=head_fraction,
            mid_fraction=mid_fraction,
            tail_fraction=tail_fraction,
            seed=seed,
        )
        chosen.extend(required_pool.items)

    selected = {item.item_id for item in chosen}
    for tier, count in zip(("head", "mid", "tail"), allocations, strict=True):
        already_in_tier = sum(item.popularity_tier == tier for item in chosen)
        if already_in_tier > count:
            raise ValueError(
                "minimum_required cannot preserve the configured popularity-tier allocation"
            )
        needed = count - already_in_tier
        available = [item for item in by_tier[tier] if item.item_id not in selected]
        if tier == "head":
            additions = available[:needed]
        elif needed:
            indices = np.sort(
                rng.choice(len(available), size=min(needed, len(available)), replace=False)
            )
            additions = [available[int(index)] for index in indices]
        else:
            additions = []
        chosen.extend(additions)
        selected.update(item.item_id for item in additions)

    # Small catalogs/tier rounding can create a deficit. Fill by global rank without duplicates.
    for item in sorted(catalog, key=lambda value: (value.popularity_rank, value.item_id)):
        if len(chosen) >= size:
            break
        if item.item_id not in selected:
            chosen.append(item)
            selected.add(item.item_id)
    if len(chosen) != size:
        raise AssertionError("Candidate pool allocation failed")
    if any(count > 1 for count in Counter(item.item_id for item in chosen).values()):
        raise AssertionError("Candidate pool contains duplicate item IDs")
    if len(required_ids.intersection(selected)) < required_target:
        raise AssertionError("Candidate pool failed its required-item opportunity target")
    if shuffle_items:
        order = rng.permutation(len(chosen))
        chosen = [chosen[int(index)] for index in order]
    return CandidatePool(tuple(chosen))
