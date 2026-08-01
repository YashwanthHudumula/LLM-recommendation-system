"""Local Ollama chat adapter with immutable installed-model verification."""

from __future__ import annotations

from typing import Any

import httpx

from recllm_fairness.models.base_client import LLMResponse, RetryingHTTPClient


class OllamaClient(RetryingHTTPClient):
    def __init__(
        self,
        *,
        model: str,
        endpoint: str,
        expected_digest: str,
        think: bool = False,
        keep_alive: str = "10m",
        num_ctx: int = 4096,
    ) -> None:
        super().__init__(timeout_seconds=600.0, max_attempts=2)
        if len(expected_digest) < 12:
            raise ValueError("Ollama expected_digest must contain at least 12 hexadecimal digits")
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.expected_digest = expected_digest.casefold()
        self.think = think
        self.keep_alive = keep_alive
        self.num_ctx = num_ctx
        self._resolved_digest: str | None = None

    async def verify_model(self) -> str:
        """Resolve the installed manifest and reject tag drift before inference."""
        response = await self._get(f"{self.endpoint}/tags")
        data = response.json()
        matches = [
            entry
            for entry in data.get("models", [])
            if entry.get("name") == self.model or entry.get("model") == self.model
        ]
        if not matches:
            raise ValueError(f"Configured Ollama model is not installed: {self.model}")
        digest = str(matches[0].get("digest", "")).casefold()
        if not digest.startswith(self.expected_digest):
            raise ValueError(
                f"Ollama digest mismatch for {self.model}: expected "
                f"{self.expected_digest}, installed {digest or '<missing>'}"
            )
        self._resolved_digest = digest
        return digest

    async def complete(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        digest = self._resolved_digest or await self.verify_model()
        try:
            response = await self._post(
                f"{self.endpoint}/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                    "think": self.think,
                    "keep_alive": self.keep_alive,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                        "num_ctx": self.num_ctx,
                    },
                },
            )
        except httpx.HTTPStatusError as error:
            detail = error.response.text.strip() or "<empty response body>"
            raise RuntimeError(f"Ollama failed for {self.model}: {detail}") from error
        data: dict[str, Any] = response.json()
        message = data.get("message", {})
        return LLMResponse(
            text=str(message.get("content", "")),
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            model=f"{self.model}@{digest}",
            raw=data,
        )

    async def runtime_status(self) -> dict[str, Any] | None:
        """Return Ollama's loaded-model VRAM/offload record when available."""
        response = await self._get(f"{self.endpoint}/ps")
        for entry in response.json().get("models", []):
            if entry.get("name") == self.model or entry.get("model") == self.model:
                return dict(entry)
        return None

    async def unload(self) -> None:
        """Release the model after sequential benchmarking on memory-limited hosts."""
        await self._post(
            f"{self.endpoint}/chat",
            json={"model": self.model, "messages": [], "stream": False, "keep_alive": 0},
        )
