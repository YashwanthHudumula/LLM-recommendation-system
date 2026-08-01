"""Validated schema for the immutable per-query source of truth."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_id: str
    persona_id: str
    model: str
    model_snapshot: str
    domain: Literal["movie", "music"]
    trait: str
    trait_level: Literal["low", "neutral", "high"]
    phrasing_variant: str
    stated_preferences: str
    relevant_item_ids: list[str] = Field(default_factory=list)
    repeat_idx: int = Field(ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    system_prompt: str
    user_prompt: str
    prompt_sha256: str
    candidate_item_ids: list[str]
    raw_response_text: str
    parsed_titles: list[str]
    matched_item_ids: list[str]
    hallucinated_titles: list[str]
    off_list_titles: list[str] = Field(default_factory=list)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


IDENTITY_COLUMNS = [
    "persona_id",
    "model",
    "domain",
    "trait",
    "trait_level",
    "phrasing_variant",
    "repeat_idx",
]
