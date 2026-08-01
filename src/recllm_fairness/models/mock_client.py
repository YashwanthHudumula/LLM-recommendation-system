"""No-cost deterministic client used to exercise the complete research pipeline."""

from __future__ import annotations

import hashlib
import re

from recllm_fairness.models.base_client import LLMResponse

_CANDIDATE_LINE = re.compile(r"^(C\d{3}\s*\|\s*.+?)\s*$", re.MULTILINE)


class MockClient:
    def __init__(self, model: str = "deterministic-catalog-v1") -> None:
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        candidates = _CANDIDATE_LINE.findall(user_prompt)
        if not candidates:
            raise ValueError("Mock client requires a coded candidate catalog")
        requested = re.search(r"exactly (\d+)", user_prompt, re.IGNORECASE)
        top_k = min(int(requested.group(1)) if requested else 10, len(candidates))
        personality_lines = [
            line
            for line in user_prompt.splitlines()
            if line.startswith("I ") and not line.startswith("I would")
        ]
        key = "|".join(personality_lines).encode()
        offset = int.from_bytes(hashlib.sha256(key).digest()[:2], "big") % len(candidates)
        selected = [candidates[(offset + index) % len(candidates)] for index in range(top_k)]
        text = "\n".join(f"{index}. {title}" for index, title in enumerate(selected, 1))
        return LLMResponse(
            text=text,
            prompt_tokens=max(1, len((system_prompt + user_prompt).split())),
            completion_tokens=max(1, len(text.split())),
            model=self.model,
            raw={"mock": True, "temperature": temperature, "max_tokens": max_tokens},
        )
