"""JSON Schemas for Claude structured outputs.

These are passed verbatim to ``output_config.format`` so each LLM call returns
validated, parseable JSON. Every object sets ``additionalProperties: false`` and
lists all keys in ``required`` (a structured-outputs requirement). Numeric and
string *constraints* (min/max, minLength, …) are intentionally omitted — they
are not supported by structured outputs.
"""

from __future__ import annotations

from typing import Any


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    """Build a strict object schema requiring all of its properties."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_STR = {"type": "string"}
_STR_LIST = {"type": "array", "items": {"type": "string"}}
_INT = {"type": "integer"}


RESEARCH_SCHEMA = _obj(
    {
        "company_overview": _STR,
        "industry": _STR,
        "estimated_size": _STR,
        "buying_signals": _STR_LIST,
        "icp_fit_notes": _STR,
        "key_people": _STR_LIST,
    }
)


QUALIFICATION_SCHEMA = _obj(
    {
        "status": {"type": "string", "enum": ["qualified", "needs_discovery", "disqualified"]},
        "fit_score": _INT,  # 0-100, ICP fit
        "intent_score": _INT,  # 0-100, buying intent
        "rationale": _STR,
        "missing_info": _STR_LIST,  # what discovery must answer before qualifying
    }
)


DISCOVERY_SCHEMA = _obj(
    {
        "captured": {
            "type": "array",
            "items": _obj({"question": _STR, "answer": _STR}),
        },
        "open_questions": _STR_LIST,
        "summary": _STR,
    }
)


RECOMMENDATION_SCHEMA = _obj(
    {
        "next_best_action": _STR,
        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
        "outreach_channel": _STR,
        "outreach_subject": _STR,
        "outreach_body": _STR,
        "talking_points": _STR_LIST,
    }
)
