"""The GTM graph nodes.

Each node reads from :class:`~gtm_agent.state.GTMState`, calls the (mock) tools
and/or Claude, and returns a partial state update. Nodes are intentionally small
and side-effect-free apart from the LLM/tool calls.
"""

from __future__ import annotations

import json
from typing import Any

from . import llm, prompts, security, tools
from .schemas import (
    DISCOVERY_SCHEMA,
    QUALIFICATION_SCHEMA,
    RECOMMENDATION_SCHEMA,
    RESEARCH_SCHEMA,
)
from .state import GTMState

# Bounds the discovery↔qualify loop so we never cycle forever.
MAX_DISCOVERY_ROUNDS = 2


def _identifier(lead: dict[str, Any]) -> str:
    return str(lead.get("domain") or lead.get("company") or "").strip()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def research_node(state: GTMState) -> dict[str, Any]:
    """Pull account data from the tools and distill it into a research brief."""
    # The lead is user-supplied input — sanitize it before it touches a prompt,
    # and persist the cleaned version so downstream nodes use it too.
    lead, lead_flags = security.sanitize_value(state["lead"])
    ident = _identifier(lead)

    firmographics = tools.enrich_account(ident)
    signals = tools.search_buying_signals(ident)
    crm = tools.get_crm_record(ident)

    user = (
        "Produce the research brief from the account data below.\n\n"
        + security.untrusted_block("lead", lead)
        + "\n\n"
        + security.untrusted_block("firmographic_enrichment", firmographics)
        + "\n\n"
        + security.untrusted_block("buying_signals", signals)
        + "\n\n"
        + security.untrusted_block("crm_record", crm)
    )
    summary = llm.extract(prompts.RESEARCH_SYSTEM, user, RESEARCH_SCHEMA)

    research = {**summary, "raw": {"firmographics": firmographics, "signals": signals, "crm": crm}}
    company = firmographics.get("company", lead.get("company", "the account"))
    log = [f"Researched {company}: {len(signals)} signal(s) found."]
    if lead_flags:
        log.append(f"[!] Sanitized suspicious content in lead input: {', '.join(lead_flags)}.")
    return {"lead": lead, "research": research, "stage": "research", "log": log}


def qualify_node(state: GTMState) -> dict[str, Any]:
    """Score the account against the ICP, possibly using prior discovery."""
    research = state.get("research", {})
    discovery = state.get("discovery", {})

    summary = {k: v for k, v in research.items() if k != "raw"}
    user = (
        "Qualify this account.\n\n"
        f"Account research summary (trusted, model-generated):\n{_json(summary)}\n\n"
        + security.untrusted_block("raw_signals_and_crm", research.get("raw", {}))
        + "\n\n"
        + security.untrusted_block("discovery_answers", discovery.get("captured", []))
    )
    verdict = llm.extract(prompts.QUALIFY_SYSTEM, user, QUALIFICATION_SCHEMA)

    status = verdict.get("status", "needs_discovery")
    return {
        "qualification": verdict,
        "stage": "qualify",
        "log": [
            f"Qualification: {status} "
            f"(fit={verdict.get('fit_score')}, intent={verdict.get('intent_score')})."
        ],
    }


def discovery_node(state: GTMState) -> dict[str, Any]:
    """Answer the qualifier's open questions from call transcripts / account data."""
    lead = state["lead"]
    ident = _identifier(lead)

    transcripts = tools.get_call_transcripts(ident)
    qualification = state.get("qualification", {})
    missing = qualification.get("missing_info", [])
    prior = state.get("discovery", {}).get("captured", [])

    research_summary = {k: v for k, v in state.get("research", {}).items() if k != "raw"}
    user = (
        "Capture every answer supported by the evidence and list what remains open.\n\n"
        f"Open items to resolve, from qualification (trusted):\n{_json(missing)}\n\n"
        f"Account research summary (trusted):\n{_json(research_summary)}\n\n"
        + security.untrusted_block("already_captured_answers", prior)
        + "\n\n"
        + security.untrusted_block("call_transcripts", transcripts)
    )
    result = llm.extract(prompts.DISCOVERY_SYSTEM, user, DISCOVERY_SCHEMA)

    # Merge newly-captured answers with prior ones, de-duped by question text.
    seen = {str(item.get("question", "")).strip().lower() for item in prior}
    merged = list(prior)
    for item in result.get("captured", []):
        key = str(item.get("question", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item)

    discovery = {
        "captured": merged,
        "open_questions": result.get("open_questions", []),
        "summary": result.get("summary", ""),
    }
    rounds = state.get("discovery_rounds", 0) + 1
    return {
        "discovery": discovery,
        "discovery_rounds": rounds,
        "stage": "discovery",
        "log": [
            f"Discovery round {rounds}: captured {len(result.get('captured', []))} new answer(s), "
            f"{len(discovery['open_questions'])} still open."
        ],
    }


def recommend_node(state: GTMState) -> dict[str, Any]:
    """Produce the next-best-action and outreach draft."""
    research = state.get("research", {})
    summary = {k: v for k, v in research.items() if k != "raw"}
    user = (
        "Recommend the next best action and draft the outreach.\n\n"
        f"Account research summary (trusted):\n{_json(summary)}\n\n"
        f"Qualification (trusted):\n{_json(state.get('qualification', {}))}\n\n"
        + security.untrusted_block("discovery", state.get("discovery", {}))
        + "\n\n"
        + security.untrusted_block("lead_contact", state.get("lead", {}))
    )
    recommendation = llm.extract(prompts.RECOMMEND_SYSTEM, user, RECOMMENDATION_SCHEMA)
    return {
        "recommendation": recommendation,
        "stage": "recommend",
        "log": [
            f"Recommendation: {recommendation.get('next_best_action', '(none)')} "
            f"[priority={recommendation.get('priority')}]."
        ],
    }
