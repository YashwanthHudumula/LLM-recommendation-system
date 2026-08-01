"""Validated config-to-client factory with no provider details leaking outward."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, cast

from recllm_fairness.models.anthropic_client import AnthropicClient
from recllm_fairness.models.base_client import LLMClient
from recllm_fairness.models.google_client import GoogleClient
from recllm_fairness.models.hf_client import HuggingFaceClient
from recllm_fairness.models.mock_client import MockClient
from recllm_fairness.models.ollama_client import OllamaClient
from recllm_fairness.models.openai_client import OpenAIClient


def create_client(name: str, models_config: Mapping[str, Any]) -> LLMClient:
    if name not in models_config:
        raise KeyError(f"Unknown configured model: {name}")
    config = models_config[name]
    if not config.get("enabled", False):
        raise ValueError(f"Model {name} is disabled in config/models.yaml")
    provider = config["provider"]
    model = config["model"]
    if provider == "mock":
        return MockClient(model)
    if provider == "ollama":
        return OllamaClient(
            model=model,
            endpoint=config["endpoint"],
            expected_digest=config["expected_digest"],
            think=bool(config.get("think", False)),
            keep_alive=str(config.get("keep_alive", "10m")),
            num_ctx=int(config.get("num_ctx", 4096)),
        )
    if model == "SET_AT_COLLECTION_TIME":
        raise ValueError(f"Set and record an immutable model snapshot for {name} before collection")
    key_name = config.get("api_key_env")
    api_key = os.environ.get(key_name, "") if key_name else ""
    if not api_key:
        raise ValueError(f"Missing API credential environment variable {key_name}")
    kwargs = {"api_key": api_key, "model": model, "endpoint": config["endpoint"]}
    factories = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
        "google": GoogleClient,
        "huggingface": HuggingFaceClient,
    }
    try:
        return cast(LLMClient, factories[provider](**kwargs))
    except KeyError as error:
        raise ValueError(f"Unsupported provider: {provider}") from error
