"""OpenAI Responses API adapter implemented directly over HTTP."""

from __future__ import annotations

from recllm_fairness.models.base_client import LLMResponse, RetryingHTTPClient


class OpenAIClient(RetryingHTTPClient):
    def __init__(self, *, api_key: str, model: str, endpoint: str) -> None:
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint

    async def complete(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "instructions": system_prompt,
            "input": user_prompt,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        response = await self._post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
        )
        data = response.json()
        text_parts = [
            content.get("text", "")
            for output in data.get("output", [])
            for content in output.get("content", [])
            if content.get("type") in {"output_text", "text"}
        ]
        usage = data.get("usage", {})
        return LLMResponse(
            text="".join(text_parts),
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
            model=data.get("model", self.model),
            raw=data,
        )
