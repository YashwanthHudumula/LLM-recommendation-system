from __future__ import annotations

import asyncio

import httpx
import pytest

from recllm_fairness.models.ollama_client import OllamaClient


class StubOllamaClient(OllamaClient):
    async def _get(self, url: str, **kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", url)
        if url.endswith("/tags"):
            return httpx.Response(
                200,
                request=request,
                json={"models": [{"name": "qwen3:8b", "digest": "abc123def4567890"}]},
            )
        return httpx.Response(200, request=request, json={"models": []})

    async def _post(self, url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "model": "qwen3:8b",
                "message": {"role": "assistant", "content": "1. Alpha"},
                "prompt_eval_count": 12,
                "eval_count": 4,
            },
        )


def test_ollama_client_verifies_digest_and_maps_usage() -> None:
    client = StubOllamaClient(
        model="qwen3:8b",
        endpoint="http://localhost:11434/api",
        expected_digest="abc123def456",
    )
    response = asyncio.run(client.complete("system", "user", 0.7, 50))
    assert response.text == "1. Alpha"
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 4
    assert response.model == "qwen3:8b@abc123def4567890"
    asyncio.run(client.aclose())


def test_ollama_client_rejects_manifest_drift() -> None:
    client = StubOllamaClient(
        model="qwen3:8b",
        endpoint="http://localhost:11434/api",
        expected_digest="ffffffffffff",
    )
    with pytest.raises(ValueError, match="digest mismatch"):
        asyncio.run(client.verify_model())
    asyncio.run(client.aclose())
