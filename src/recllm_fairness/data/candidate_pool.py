"""Deterministic fixed candidate pools for anti-hallucination prompting."""

from __future__ import annotations

from collections import Counter
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
        return "\n".join(f"{index}. {item.title}" for index, item in enumerate(self.items, 1))


def build_candidate_pool(
    catalog: list[Item],
    *,
    size: int,
    head_fraction: float,
    mid_fraction: float,
    tail_fraction: float,
    seed: int,
) -> CandidatePool:
    """Take most-popular head items and random deterministic mid/tail samples."""
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
    for tier, count in zip(("head", "mid", "tail"), allocations, strict=True):
        available = by_tier[tier]
        if tier == "head":
            chosen.extend(available[:count])
        elif count:
            indices = np.sort(
                rng.choice(len(available), size=min(count, len(available)), replace=False)
            )
            chosen.extend(available[int(index)] for index in indices)

    # Small catalogs/tier rounding can create a deficit. Fill by global rank without duplicates.
    selected = {item.item_id for item in chosen}
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
    return CandidatePool(tuple(chosen))
