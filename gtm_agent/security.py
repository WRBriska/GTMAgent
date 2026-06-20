"""Prompt-injection defense for untrusted content.

Everything the agent reads from the outside world — CRM notes, call transcripts,
firmographic enrichment, buying signals, and the lead fields themselves — is
attacker-influenceable and gets re-injected into LLM prompts. This module is the
write-boundary filter for that content. It is **defense-in-depth**, not a
complete solution; it pairs with prompt-level isolation (see ``untrusted_block``
and the security directive in :mod:`gtm_agent.prompts`).

Two layers here:

1. :func:`sanitize_value` strips known control tokens and neutralizes explicit
   override phrases from untrusted strings (recursively, for dicts/lists).
2. :func:`untrusted_block` fences sanitized content in ``<untrusted_data>`` tags
   so the model is told, structurally, that it is data and not instructions.

Patterns are conservative: they target artifacts with no legitimate reason to
appear in CRM/firmographic/transcript text, so real data passes through intact.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Cap any single untrusted string so a planted wall of text can't crowd out the
# real instructions or blow the context budget.
MAX_TEXT_LEN = 8000

# Chat-template / control tokens and role-delimiter tags an attacker could use
# to fake a system/assistant turn or break out of our fencing. Stripped outright.
_INJECTION_TOKEN_PATTERNS = (
    re.compile(r"<\|im_(?:start|end|sep)\|>", re.IGNORECASE),
    re.compile(r"<\|(?:system|user|assistant)\|>", re.IGNORECASE),
    re.compile(r"<\|fim_(?:prefix|middle|suffix)\|>", re.IGNORECASE),
    re.compile(r"<\|endoftext\|>", re.IGNORECASE),
    re.compile(r"\[/?INST\]"),
    re.compile(r"<</?SYS>>"),
    # Our own fence + any spoofed role/system tags — prevents a planted
    # "</untrusted_data>" from closing the wrapper early.
    re.compile(r"</?untrusted[a-z_]*(?:\s[^>]*)?>", re.IGNORECASE),
    re.compile(r"</?system[_-]?prompt(?:\s[^>]*)?>", re.IGNORECASE),
    re.compile(r"</?(?:system|assistant|user|developer)(?:[_-](?:message|turn|prompt))?(?:\s[^>]*)?>", re.IGNORECASE),
)

# Natural-language attempts to override the agent's instructions. Replaced with a
# visible marker rather than deleted, so analysts can see the attempt and the
# model sees that something was scrubbed.
_OVERRIDE_PHRASE_PATTERNS = (
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|earlier|preceding|foregoing)\s+"
        r"(?:instructions?|rules?|context|prompts?|messages?|directions?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(?:all\s+)?(?:the\s+)?(?:previous|prior|above|earlier|preceding)\s+"
        r"(?:instructions?|rules?|context|prompts?)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as|from\s+now\s+on,?)\b", re.IGNORECASE),
    re.compile(r"\bnew\s+(?:instructions?|system\s+prompt|rules?|task)\s*[:\-]", re.IGNORECASE),
    re.compile(r"\boverride\s+(?:your|the|all)\s+(?:instructions?|rules?|system\s+prompt)", re.IGNORECASE),
    # Line that tries to start a fake system/assistant/developer turn.
    re.compile(r"(?mi)^\s*(?:system|assistant|developer)\s*:", ),
)

_REDACTION = "[redacted: possible prompt injection]"


def sanitize_text(text: Any, *, max_len: int = MAX_TEXT_LEN) -> tuple[str, list[str]]:
    """Sanitize a single value to a string. Returns ``(clean, flags)``.

    ``flags`` names what was modified, e.g. ``["stripped_control_token",
    "neutralized_override_phrase", "truncated"]``.
    """
    cleaned = text if isinstance(text, str) else str(text)
    flags: list[str] = []

    for pattern in _INJECTION_TOKEN_PATTERNS:
        new = pattern.sub("", cleaned)
        if new != cleaned:
            flags.append("stripped_control_token")
            cleaned = new

    for pattern in _OVERRIDE_PHRASE_PATTERNS:
        new = pattern.sub(_REDACTION, cleaned)
        if new != cleaned:
            flags.append("neutralized_override_phrase")
            cleaned = new

    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + " …[truncated]"
        flags.append("truncated")

    return cleaned, sorted(set(flags))


def sanitize_value(value: Any) -> tuple[Any, list[str]]:
    """Recursively sanitize all strings inside a value. Returns ``(clean, flags)``.

    Non-string scalars (int/float/bool/None) pass through unchanged.
    """
    flags: list[str] = []

    def _walk(node: Any) -> Any:
        if isinstance(node, str):
            clean, found = sanitize_text(node)
            flags.extend(found)
            return clean
        if isinstance(node, dict):
            return {key: _walk(val) for key, val in node.items()}
        if isinstance(node, (list, tuple)):
            return [_walk(item) for item in node]
        return node

    return _walk(value), sorted(set(flags))


def untrusted_block(label: str, payload: Any) -> str:
    """Fence sanitized untrusted content for inclusion in a prompt.

    The payload is sanitized again here (idempotent) so this is safe to call on
    anything, then serialized and wrapped in a clearly-labeled tag the system
    prompt tells the model to treat as data, never instructions.
    """
    clean, _ = sanitize_value(payload)
    body = clean if isinstance(clean, str) else json.dumps(clean, ensure_ascii=False, indent=2, default=str)
    return f'<untrusted_data source="{label}">\n{body}\n</untrusted_data>'
