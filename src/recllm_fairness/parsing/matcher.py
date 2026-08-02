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


class TitleMatcher:
    """Reusable full-catalog index for efficient collection and analysis re-grounding."""

    def __init__(self, catalog: list[Item]) -> None:
        if not catalog:
            raise ValueError("Cannot match against an empty catalog")
        self.ordered = sorted(catalog, key=lambda item: (item.popularity_rank, item.item_id))
        self.choices = [normalize_title(item.title) for item in self.ordered]
        self.exact_indices: dict[str, list[int]] = {}
        for index, choice in enumerate(self.choices):
            self.exact_indices.setdefault(choice, []).append(index)

    def match(
        self,
        titles: list[str],
        *,
        allowed_item_ids: set[str] | frozenset[str] | None = None,
        threshold: float = 88.0,
        ambiguity_margin: float = 3.0,
    ) -> MatchResult:
        """Match against the indexed catalog, then enforce the injected pool."""
        matched: list[str] = []
        hallucinated: list[str] = []
        off_list: list[str] = []
        scores: list[float] = []
        used: set[str] = set()
        for raw_title in titles:
            query = normalize_title(raw_title)
            exact = self.exact_indices.get(query, [])
            if exact:
                eligible = [
                    index
                    for index in exact
                    if allowed_item_ids is None
                    or self.ordered[index].item_id in allowed_item_ids
                ]
                if not eligible:
                    off_list.append(raw_title)
                    continue
                item = self.ordered[eligible[0]]
                if item.item_id not in used:
                    matched.append(item.item_id)
                    scores.append(100.0)
                    used.add(item.item_id)
                continue
            candidates = process.extract(query, self.choices, scorer=fuzz.WRatio, limit=2)
            if not candidates or candidates[0][1] < threshold:
                hallucinated.append(raw_title)
                continue
            best_score = float(candidates[0][1])
            if (
                len(candidates) > 1
                and best_score - float(candidates[1][1]) < ambiguity_margin
                and not (best_score == 100.0 and candidates[0][0] == candidates[1][0])
            ):
                hallucinated.append(raw_title)
                continue
            item = self.ordered[int(candidates[0][2])]
            if allowed_item_ids is not None and item.item_id not in allowed_item_ids:
                off_list.append(raw_title)
                continue
            if item.item_id not in used:
                matched.append(item.item_id)
                scores.append(best_score)
                used.add(item.item_id)
        return MatchResult(matched, hallucinated, off_list, scores)


def match_titles(
    titles: list[str],
    catalog: list[Item],
    *,
    allowed_item_ids: set[str] | frozenset[str] | None = None,
    threshold: float = 88.0,
    ambiguity_margin: float = 3.0,
) -> MatchResult:
    """One-shot convenience wrapper around :class:`TitleMatcher`."""
    return TitleMatcher(catalog).match(
        titles,
        allowed_item_ids=allowed_item_ids,
        threshold=threshold,
        ambiguity_margin=ambiguity_margin,
    )
