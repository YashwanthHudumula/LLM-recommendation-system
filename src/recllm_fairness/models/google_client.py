"""Google Gemini generateContent API adapter."""

from __future__ import annotations

from recllm_fairness.models.base_client import LLMResponse, RetryingHTTPClient


class GoogleClient(RetryingHTTPClient):
    def __init__(self, *, api_key: str, model: str, endpoint: str) -> None:
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint.rstrip("/")

    async def complete(
        self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        url = f"{self.endpoint}/models/{self.model}:generateContent?key={self.api_key}"
        response = await self._post(
            url,
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            },
        )
        data = response.json()
        text = "".join(
            part.get("text", "")
            for candidate in data.get("candidates", [])[:1]
            for part in candidate.get("content", {}).get("parts", [])
        )
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            text=text,
            prompt_tokens=int(usage.get("promptTokenCount", 0)),
            completion_tokens=int(usage.get("candidatesTokenCount", 0)),
            model=self.model,
            raw=data,
        )

