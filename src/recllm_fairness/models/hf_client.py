"""Hugging Face OpenAI-compatible inference router adapter."""

from __future__ import annotations

from recllm_fairness.models.base_client import LLMResponse, RetryingHTTPClient


class HuggingFaceClient(RetryingHTTPClient):
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
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        data = response.json()
        usage = data.get("usage", {})
        text = data["choices"][0]["message"]["content"]
        return LLMResponse(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            model=data.get("model", self.model),
            raw=data,
        )
