"""Pre-spend semantic-equivalence gate for prompt phrasing variants."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Protocol, cast

import numpy as np

from recllm_fairness.personas.phrasing import PHRASING_TEMPLATES, render_instruction


class Encoder(Protocol):
    def encode(self, sentences: list[str], *, normalize_embeddings: bool) -> np.ndarray: ...


@dataclass(frozen=True)
class SemanticCheckResult:
    minimum_similarity: float
    pairwise_similarities: dict[str, float]


def check_phrasing_equivalence(
    encoder: Encoder,
    *,
    threshold: float,
    domain: str = "movie",
    top_k: int = 10,
) -> SemanticCheckResult:
    """Embed every surface form and reject any pair below the threshold."""
    names = list(PHRASING_TEMPLATES)
    sentences = [render_instruction(name, domain, top_k) for name in names]
    embeddings = np.asarray(encoder.encode(sentences, normalize_embeddings=True), dtype=float)
    if embeddings.shape[0] != len(names):
        raise ValueError("Encoder returned the wrong number of embeddings")
    scores: dict[str, float] = {}
    for left, right in combinations(range(len(names)), 2):
        score = float(np.dot(embeddings[left], embeddings[right]))
        scores[f"{names[left]}::{names[right]}"] = score
    minimum = min(scores.values())
    if minimum < threshold:
        failing = {name: value for name, value in scores.items() if value < threshold}
        raise ValueError(f"Phrasing semantic-equivalence gate failed: {failing}")
    return SemanticCheckResult(minimum, scores)


def load_sentence_transformer(model_name: str) -> Encoder:
    """Lazy-load the heavyweight optional model only when validation is requested."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:  # pragma: no cover - exercised in minimal environments
        raise RuntimeError("Install project dependencies to run semantic validation") from error
    return cast(Encoder, SentenceTransformer(model_name))
