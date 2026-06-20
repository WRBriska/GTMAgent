"""Tool interface over the (mocked) external systems.

Each function is the seam where a real integration would live. They all resolve
an account once and return a slice of it, so the nodes never touch
:mod:`gtm_agent.mock_data` directly. To go live, reimplement these four against
your CRM / enrichment / intent / call-recording providers — the node code and
graph stay unchanged.
"""

from __future__ import annotations

from typing import Any

from . import mock_data, security


def _resolve(identifier: str) -> dict[str, Any]:
    return mock_data.lookup(identifier) or mock_data.synthesize(identifier)


def _clean(value: Any) -> Any:
    """Sanitize external data at the boundary, before it can reach a prompt."""
    cleaned, _ = security.sanitize_value(value)
    return cleaned


def enrich_account(identifier: str) -> dict[str, Any]:
    """Firmographic enrichment for a company name or domain."""
    record = _resolve(identifier)
    return _clean({"company": record["company"], "domain": record["domain"], **record["firmographics"]})


def search_buying_signals(identifier: str) -> list[str]:
    """Recent buying-intent / news signals for the account."""
    return _clean(list(_resolve(identifier).get("signals", [])))


def get_crm_record(identifier: str) -> dict[str, Any]:
    """Current CRM state for the account (stage, owner, activity, notes)."""
    return _clean(dict(_resolve(identifier).get("crm", {})))


def get_call_transcripts(identifier: str) -> list[dict[str, str]]:
    """Discovery/sales call transcript snippets for the account."""
    return _clean(list(_resolve(identifier).get("transcripts", [])))
