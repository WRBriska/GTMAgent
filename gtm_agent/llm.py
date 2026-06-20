"""Thin Claude helpers for the GTM nodes.

``extract`` performs a single-shot structured call: it asks Claude to return
JSON matching a schema (via ``output_config.format``) and returns the parsed
dict. It degrades gracefully on older SDKs/models that don't support
``output_config`` by re-asking for strict JSON and tolerantly parsing the text.

No sampling parameters (``temperature``/``top_p``/``top_k``) are ever sent —
they are rejected by Claude Opus 4.8, the default model.
"""

from __future__ import annotations

import json
import re
from typing import Any

import anthropic

from .config import get_client, get_model

# Structured extraction is short; well under the streaming threshold.
_MAX_TOKENS = 4096


def _response_text(resp: Any) -> str:
    return "".join(
        getattr(block, "text", "") for block in resp.content if getattr(block, "type", None) == "text"
    )


def _loads(text: str) -> dict[str, Any]:
    """Parse JSON, tolerating code fences and surrounding prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def extract(system: str, user: str, schema: dict[str, Any], *, max_tokens: int = _MAX_TOKENS) -> dict[str, Any]:
    """Call Claude and return a dict validated against ``schema``.

    Tries structured outputs first; falls back to plain JSON parsing if the
    installed SDK or selected model doesn't support ``output_config``.
    """
    client = get_client()
    model = get_model()

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        return _loads(_response_text(resp))
    except (TypeError, anthropic.BadRequestError):
        # SDK without output_config kwarg, or a model that doesn't support it.
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system
            + "\n\nReturn STRICT JSON only — an object with exactly the requested "
            "fields. No prose, no markdown, no code fences.",
            messages=[{"role": "user", "content": user}],
        )
        return _loads(_response_text(resp))


def generate_text(system: str, user: str, *, max_tokens: int = _MAX_TOKENS) -> str:
    """Single-shot plain-text Claude call."""
    resp = get_client().messages.create(
        model=get_model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _response_text(resp).strip()
