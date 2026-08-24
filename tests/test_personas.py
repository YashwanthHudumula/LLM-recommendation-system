from __future__ import annotations

import numpy as np
import pytest

from recllm_fairness.personas.generator import assert_counterfactual_control, generate_personas
from recllm_fairness.personas.phrasing import render_instruction
from recllm_fairness.personas.semantic_check import check_phrasing_equivalence


class PerfectEncoder:
    def encode(self, sentences: list[str], *, normalize_embeddings: bool) -> np.ndarray:
        return np.tile(np.array([[1.0, 0.0]]), (len(sentences), 1))


def test_generator_holds_preferences_fixed_across_counterfactuals() -> None:
    conditions = generate_personas(
        preferences={"movie": ["preference"]},
        personas_per_cell=2,
        traits=["openness"],
        levels=["low", "neutral", "high"],
        phrasing_variants=["formal", "casual"],
        domains=("movie",),
    )
    assert len(conditions) == 12
    assert_counterfactual_control(conditions)
    assert all(
        not condition.trait_marker for condition in conditions if condition.trait_level == "neutral"
    )


def test_semantic_check_is_a_loud_gate() -> None:
    result = check_phrasing_equivalence(PerfectEncoder(), threshold=0.9)
    assert result.minimum_similarity == pytest.approx(1.0)


def test_generator_has_exactly_eleven_trait_framings_per_preference() -> None:
    conditions = generate_personas(
        preferences={"movie": [{"id": "M1", "text": "science fiction"}]},
        personas_per_cell=1,
        traits=[
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ],
        levels=["low", "neutral", "high"],
        phrasing_variants=["direct"],
        domains=("movie",),
    )
    assert len(conditions) == 11
    neutral = [condition for condition in conditions if condition.trait_level == "neutral"]
    assert len(neutral) == 1
    assert neutral[0].trait == "neutral"
    assert neutral[0].persona_id == "movie-M1"


def test_instruction_requires_verbatim_candidate_names() -> None:
    instruction = render_instruction("direct", "movie", 10)
    assert "catalog as closed" in instruction
    assert "C### | exact candidate name" in instruction
    assert "do not recommend anything from memory" in instruction
