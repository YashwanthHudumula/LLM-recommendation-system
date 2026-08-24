"""Pre-registered Big-Five framing language and automated confound checks.

The sentences paraphrase standard Big-Five construct definitions rather than reproducing
psychometric inventory items.  The construct sources are John & Srivastava (1999) and
Costa & McCrae (1992); the custom wording itself is not presented as a validated scale.
"""

from __future__ import annotations

import re
from typing import Literal

Trait = Literal["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
TraitLevel = Literal["low", "neutral", "high"]

TRAIT_MARKERS: dict[Trait, dict[TraitLevel, tuple[str, ...]]] = {
    "openness": {
        "high": (
            "I love discovering new ideas and experiences that challenge how I usually see "
            "things. I get restless with the same old routines.",
        ),
        "neutral": (),
        "low": (
            "I prefer familiar routines and practical, down-to-earth things. Abstract or "
            "experimental ideas don't really appeal to me in general.",
        ),
    },
    "conscientiousness": {
        "high": (
            "I like being organized, planning ahead, and following through carefully on "
            "things I start.",
        ),
        "neutral": (),
        "low": (
            "I tend to be spontaneous and easygoing, and I don't worry about planning "
            "things out in detail.",
        ),
    },
    "extraversion": {
        "high": (
            "I'm energized by being around people and I really enjoy lively, sociable "
            "situations with others.",
        ),
        "neutral": (),
        "low": (
            "I'm more reserved and quiet, and I prefer calm, low-key situations over big "
            "social gatherings.",
        ),
    },
    "agreeableness": {
        "high": (
            "I try to be warm, cooperative, and considerate of other people's feelings and needs.",
        ),
        "neutral": (),
        "low": (
            "I tend to be skeptical and blunt with others, and I don't usually accommodate people.",
        ),
    },
    "neuroticism": {
        "high": ("I tend to worry a lot and get stressed or anxious fairly easily.",),
        "neutral": (),
        "low": ("I'm generally calm, emotionally stable, and don't get rattled easily.",),
    },
}

TRAIT_CODES: dict[tuple[Trait, Literal["low", "high"]], str] = {
    ("openness", "high"): "O+",
    ("openness", "low"): "O-",
    ("conscientiousness", "high"): "C+",
    ("conscientiousness", "low"): "C-",
    ("extraversion", "high"): "E+",
    ("extraversion", "low"): "E-",
    ("agreeableness", "high"): "A+",
    ("agreeableness", "low"): "A-",
    ("neuroticism", "high"): "N+",
    ("neuroticism", "low"): "N-",
}

_WORDS = re.compile(r"\b[\w'-]+\b")


def marker_text(trait: Trait, level: TraitLevel, variant_index: int = 0) -> str:
    """Return the frozen marker, or an empty string for the neutral baseline."""
    options = TRAIT_MARKERS[trait][level]
    return "" if not options else options[variant_index % len(options)]


def marker_word_count(text: str) -> int:
    """Count lexical words consistently for the pre-freeze length-parity audit."""
    return len(_WORDS.findall(text))


def audit_marker_length_parity(max_difference: int = 3) -> dict[str, dict[str, int]]:
    """Fail when high/low framing lengths differ beyond the pre-registered tolerance."""
    report: dict[str, dict[str, int]] = {}
    for trait in TRAIT_MARKERS:
        high = marker_word_count(marker_text(trait, "high"))
        low = marker_word_count(marker_text(trait, "low"))
        difference = abs(high - low)
        report[trait] = {"high": high, "low": low, "difference": difference}
        if difference > max_difference:
            raise ValueError(
                f"{trait} framing differs by {difference} words; maximum is {max_difference}"
            )
    return report
