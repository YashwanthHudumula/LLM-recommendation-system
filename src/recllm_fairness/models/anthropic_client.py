"""Anthropic Messages API adapter."""

from __future__ import annotations

from recllm_fairness.models.base_client import LLMResponse, RetryingHTTPClient


class AnthropicClient(RetryingHTTPClient):
    def __init__(self, *, api_key: str, model: str, endpoint: str) -> None:
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint

    async def complete(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        response = await self._post(
            self.endpoint,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        data = response.json()
        text = "".join(part.get("text", "") for part in data.get("content", []))
        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
            model=data.get("model", self.model),
            raw=data,
        )

