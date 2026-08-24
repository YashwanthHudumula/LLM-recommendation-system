"""Semantically equivalent surface forms for the recommendation instruction."""

from __future__ import annotations

from typing import Literal

PhrasingVariant = Literal["formal", "casual", "direct", "indirect"]

PHRASING_TEMPLATES: dict[PhrasingVariant, str] = {
    "formal": (
        "Please recommend exactly {top_k} {domain_items} that match the preferences stated above. "
        "Return only an ordered list of titles selected from the candidate catalog."
    ),
    "casual": (
        "Could you pick exactly {top_k} {domain_items} that fit what I like? "
        "Just give me a ranked list of titles from the candidate catalog."
    ),
    "direct": (
        "Recommend exactly {top_k} matching {domain_items}. "
        "Output only a ranked title list from the candidate catalog."
    ),
    "indirect": (
        "I would appreciate a selection of exactly {top_k} {domain_items} suited to these "
        "preferences. "
        "A ranked list containing only titles from the candidate catalog would be ideal."
    ),
}

EXACT_COPY_SUFFIX = (
    " Treat the displayed catalog as closed: do not recommend anything from memory or outside "
    "it, even when another item seems more relevant. Return exactly {top_k} lines in the format "
    "`C### | exact candidate name`, copying both fields verbatim."
)


def render_instruction(variant: PhrasingVariant, domain: str, top_k: int) -> str:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    domain_items = "movies" if domain == "movie" else "music artists"
    return PHRASING_TEMPLATES[variant].format(
        top_k=top_k, domain_items=domain_items
    ) + EXACT_COPY_SUFFIX.format(top_k=top_k)
