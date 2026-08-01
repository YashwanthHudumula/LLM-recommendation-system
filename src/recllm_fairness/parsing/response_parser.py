"""Conservative extraction of ordered titles from common LLM output shapes."""

from __future__ import annotations

import json
import re

_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)]|\[\d+\])\s*")
_LABEL = re.compile(r"^(?:title|movie|artist|song)\s*:\s*", re.IGNORECASE)


def _clean_title(value: str) -> str:
    value = _PREFIX.sub("", value.strip())
    value = _LABEL.sub("", value)
    value = value.strip().strip('"“”\'`')
    # Do not strip hyphen-delimited suffixes: they are frequently part of canonical titles
    # (for example, "Star Wars: Episode IV - A New Hope"). Explanatory text is rejected by
    # catalog grounding rather than destructively guessed away here.
    return value.strip()


def parse_response(text: str, *, top_k: int | None = None) -> list[str]:
    """Parse JSON arrays/objects or one-title-per-line text without inventing entries."""
    if not text.strip():
        return []
    titles: list[str] = []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = parsed.get("recommendations", parsed.get("titles", []))
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, str):
                    titles.append(_clean_title(item))
                elif isinstance(item, dict) and isinstance(item.get("title"), str):
                    titles.append(_clean_title(item["title"]))
    except json.JSONDecodeError:
        for line in text.splitlines():
            cleaned = _clean_title(line)
            if cleaned and (_PREFIX.match(line) or len(text.splitlines()) == 1):
                titles.append(cleaned)
    unique: list[str] = []
    seen: set[str] = set()
    for title in titles:
        key = title.casefold()
        if title and key not in seen:
            unique.append(title)
            seen.add(key)
    return unique if top_k is None else unique[:top_k]
