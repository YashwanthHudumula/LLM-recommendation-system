"""Validated schema for the immutable per-query source of truth."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ExperimentProvenance(BaseModel):
    """Frozen identifiers that prevent cross-design collection or resume."""

    model_config = ConfigDict(frozen=True)

    design_version: str = Field(min_length=1)
    design_bundle_sha256: str = Field(pattern=SHA256_PATTERN)
    dataset_version: str = Field(min_length=1)
    collection_protocol_version: str = Field(min_length=1)

    def identity_values(self) -> tuple[str, ...]:
        return tuple(str(getattr(self, column)) for column in PROVENANCE_COLUMNS)


class QueryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal[2] = 2
    query_id: str
    design_version: str = Field(min_length=1)
    design_bundle_sha256: str = Field(pattern=SHA256_PATTERN)
    dataset_version: str = Field(min_length=1)
    collection_protocol_version: str = Field(min_length=1)
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
    response_attempts: list[str] = Field(default_factory=list)
    selected_attempt_idx: int = Field(default=0, ge=0)
    retry_user_prompt: str | None = None
    attempt_temperatures: list[float] = Field(default_factory=list)
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


LEGACY_IDENTITY_COLUMNS = [
    "persona_id",
    "model",
    "domain",
    "trait",
    "trait_level",
    "phrasing_variant",
    "repeat_idx",
]

PROVENANCE_COLUMNS = [
    "design_version",
    "design_bundle_sha256",
    "dataset_version",
    "collection_protocol_version",
]

IDENTITY_COLUMNS = [*PROVENANCE_COLUMNS, *LEGACY_IDENTITY_COLUMNS]
