"""The graph state shared across all GTM nodes.

LangGraph merges each node's returned dict into this state. Most channels are
overwrite-on-write; ``log`` uses an append reducer so every node can contribute
a line to a running narrative without clobbering earlier entries.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class GTMState(TypedDict, total=False):
    """State for the go-to-market agent.

    Keys are populated progressively as the lead moves through the pipeline.
    ``total=False`` means every key is optional — only ``lead`` must be provided
    as input.
    """

    # ── Input ────────────────────────────────────────────────────────────────
    lead: dict[str, Any]
    """The raw lead/account: e.g. {company, domain, contact_name, title, email, source}."""

    # ── Stage outputs ────────────────────────────────────────────────────────
    research: dict[str, Any]
    """Enriched account research: LLM summary + raw firmographics/signals/CRM."""

    qualification: dict[str, Any]
    """Qualification verdict: status, fit_score, intent_score, rationale, missing_info."""

    discovery: dict[str, Any]
    """Discovery results: captured Q&A, open_questions, summary."""

    recommendation: dict[str, Any]
    """Next-best-action + outreach draft + talking points."""

    # ── Control / bookkeeping ────────────────────────────────────────────────
    stage: str
    """Name of the most recently completed stage."""

    discovery_rounds: int
    """How many discovery passes have run (bounds the discovery↔qualify loop)."""

    log: Annotated[list[str], operator.add]
    """Append-only narrative of what each node did."""
