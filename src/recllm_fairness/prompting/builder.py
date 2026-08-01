"""Build final prompts from controlled persona conditions."""

from __future__ import annotations

from dataclasses import dataclass

from recllm_fairness.data.candidate_pool import CandidatePool
from recllm_fairness.personas.generator import PersonaCondition
from recllm_fairness.personas.phrasing import render_instruction
from recllm_fairness.prompting.templates import FAIRNESS_SYSTEM_SUFFIX, SYSTEM_PROMPTS


@dataclass(frozen=True)
class PromptPair:
    system_prompt: str
    user_prompt: str


def build_prompt(
    condition: PersonaCondition,
    candidate_pool: CandidatePool,
    *,
    top_k: int,
    fairness_instruction: bool = False,
) -> PromptPair:
    """Build one auditable prompt, preserving the neutral condition's missing marker."""
    system = SYSTEM_PROMPTS[condition.domain]
    if fairness_instruction:
        system += FAIRNESS_SYSTEM_SUFFIX
    sections = [f"My content preferences are: {condition.stated_preferences}."]
    if condition.trait_marker:
        sections.append(condition.trait_marker)
    sections.extend(
        [
            render_instruction(condition.phrasing_variant, condition.domain, top_k),
            "Candidate catalog (choose only from these exact titles):",
            candidate_pool.prompt_block(),
        ]
    )
    return PromptPair(system, "\n\n".join(sections))

