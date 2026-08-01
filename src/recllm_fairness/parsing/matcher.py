"""Full-catalog fuzzy grounding with explicit hallucination and off-list logging."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz, process

from recllm_fairness.data.catalog import Item

_YEAR = re.compile(r"\s*\(\d{4}\)\s*$")
_PUNCT = re.compile(r"[^\w\s]")


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = _YEAR.sub("", value)
    value = _PUNCT.sub(" ", value)
    return " ".join(value.split())


@dataclass(frozen=True)
class MatchResult:
    matched_item_ids: list[str]
    hallucinated_titles: list[str]
    off_list_titles: list[str]
    match_scores: list[float]


def match_titles(
    titles: list[str],
    catalog: list[Item],
    *,
    allowed_item_ids: set[str] | frozenset[str] | None = None,
    threshold: float = 88.0,
    ambiguity_margin: float = 3.0,
) -> MatchResult:
    """Match against the full catalog, then enforce the injected candidate pool."""
    if not catalog:
        raise ValueError("Cannot match against an empty catalog")
    ordered = sorted(catalog, key=lambda item: (item.popularity_rank, item.item_id))
    choices = [normalize_title(item.title) for item in ordered]
    matched: list[str] = []
    hallucinated: list[str] = []
    off_list: list[str] = []
    scores: list[float] = []
    used: set[str] = set()
    for raw_title in titles:
        query = normalize_title(raw_title)
        candidates = process.extract(query, choices, scorer=fuzz.WRatio, limit=2)
        if not candidates or candidates[0][1] < threshold:
            hallucinated.append(raw_title)
            continue
        best_score = float(candidates[0][1])
        if (
            len(candidates) > 1
            and best_score - float(candidates[1][1]) < ambiguity_margin
            # Exact normalized duplicates are resolved by deterministic catalog ordering.
            and not (best_score == 100.0 and candidates[0][0] == candidates[1][0])
        ):
            hallucinated.append(raw_title)
            continue
        item = ordered[int(candidates[0][2])]
        if allowed_item_ids is not None and item.item_id not in allowed_item_ids:
            off_list.append(raw_title)
            continue
        if item.item_id not in used:
            matched.append(item.item_id)
            scores.append(best_score)
            used.add(item.item_id)
    return MatchResult(matched, hallucinated, off_list, scores)
