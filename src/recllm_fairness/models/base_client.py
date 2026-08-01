"""Provider-independent response contract and retrying HTTP base class."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse: ...


class RetryingHTTPClient:
    """Shared exponential backoff with jitter for transient provider failures."""

    def __init__(self, *, timeout_seconds: float = 90.0, max_attempts: int = 5) -> None:
        self._http = httpx.AsyncClient(timeout=timeout_seconds)
        self._max_attempts = max_attempts

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("POST", url, **kwargs)

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(self._max_attempts):
            try:
                response = await self._http.request(method, url, **kwargs)
                if response.status_code not in {408, 409, 429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError):
                if attempt + 1 == self._max_attempts:
                    raise
                await asyncio.sleep((2**attempt) + random.random())
        raise AssertionError("Retry loop exhausted without returning or raising")

    async def aclose(self) -> None:
        await self._http.aclose()
