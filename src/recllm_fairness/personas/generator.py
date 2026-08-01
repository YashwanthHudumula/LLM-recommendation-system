"""Full controlled persona x trait x level x phrasing x domain matrix."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from recllm_fairness.personas.phrasing import PhrasingVariant
from recllm_fairness.personas.traits import Trait, TraitLevel, marker_text


class PersonaCondition(BaseModel):
    model_config = ConfigDict(frozen=True)

    persona_id: str
    domain: Literal["movie", "music"]
    stated_preferences: str
    relevant_item_ids: tuple[str, ...] = ()
    trait: Trait | Literal["neutral"]
    trait_level: TraitLevel
    trait_marker: str
    phrasing_variant: PhrasingVariant


def generate_personas(
    *,
    preferences: Mapping[str, Sequence[str | Mapping[str, object]]],
    personas_per_cell: int,
    traits: Iterable[Trait],
    levels: Iterable[TraitLevel],
    phrasing_variants: Iterable[PhrasingVariant],
    domains: Iterable[Literal["movie", "music"]] = ("movie", "music"),
) -> list[PersonaCondition]:
    """Generate 10 trait poles plus one shared neutral for each base preference/phrasing."""
    if personas_per_cell < 1:
        raise ValueError("personas_per_cell must be positive")
    configured_traits = tuple(traits)
    configured_levels = tuple(levels)
    configured_phrasings = tuple(phrasing_variants)
    if "neutral" not in configured_levels:
        raise ValueError("levels must include the shared neutral baseline")
    conditions: list[PersonaCondition] = []
    for domain in domains:
        domain_preferences = preferences.get(domain)
        if not domain_preferences:
            raise ValueError(f"No stated preferences configured for {domain}")
        for base_index in range(personas_per_cell):
            preference_input = domain_preferences[base_index % len(domain_preferences)]
            if isinstance(preference_input, str):
                preference_id = f"p{base_index:05d}"
                fixed_preference = preference_input
                relevant_item_ids: tuple[str, ...] = ()
            else:
                preference_id = str(preference_input.get("id", f"p{base_index:05d}"))
                fixed_preference = str(preference_input["text"])
                raw_relevant = preference_input.get("relevant_item_ids", [])
                if not isinstance(raw_relevant, Sequence) or isinstance(raw_relevant, str):
                    raise TypeError("relevant_item_ids must be a sequence of item IDs")
                relevant_item_ids = tuple(str(item_id) for item_id in raw_relevant)
            cycle = base_index // len(domain_preferences)
            suffix = "" if cycle == 0 else f"-r{cycle:03d}"
            persona_id = f"{domain}-{preference_id}{suffix}"
            for phrasing in configured_phrasings:
                conditions.append(
                    PersonaCondition(
                        persona_id=persona_id,
                        domain=domain,
                        stated_preferences=fixed_preference,
                        relevant_item_ids=relevant_item_ids,
                        trait="neutral",
                        trait_level="neutral",
                        trait_marker="",
                        phrasing_variant=phrasing,
                    )
                )
            for trait in configured_traits:
                for level in configured_levels:
                    if level == "neutral":
                        continue
                    for phrasing in configured_phrasings:
                        conditions.append(
                            PersonaCondition(
                                persona_id=persona_id,
                                domain=domain,
                                stated_preferences=fixed_preference,
                                relevant_item_ids=relevant_item_ids,
                                trait=trait,
                                trait_level=level,
                                trait_marker=marker_text(trait, level, base_index),
                                phrasing_variant=phrasing,
                            )
                        )
    return conditions


def assert_counterfactual_control(conditions: Sequence[PersonaCondition]) -> None:
    """Fail if taste text or relevance ground truth drifts across counterfactuals."""
    seen: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {}
    for condition in conditions:
        key = (condition.persona_id, condition.domain)
        value = (condition.stated_preferences, condition.relevant_item_ids)
        prior = seen.setdefault(key, value)
        if prior != value:
            raise ValueError(
                f"Preference text or relevance labels drifted for persona {condition.persona_id}"
            )
