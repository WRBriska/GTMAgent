"""
Go To Market (GTM) Agent — a self-contained LangGraph + Claude agent.

A four-stage go-to-market workflow built as a true LangGraph ``StateGraph``:

    research → qualify → (discovery ↔ qualify loop) → recommend

It is self-contained: all external systems (CRM, firmographic enrichment,
buying-signal feeds, call transcripts) are mocked in :mod:`gtm_agent.mock_data`,
so the graph runs anywhere with only an ``ANTHROPIC_API_KEY``.

The structure (typed state, checkpointer, structured LLM extraction, stage
inference) is adapted from the reference Flask discovery agent, rewritten as a
generic, vendor-neutral GTM agent.
"""

from .graph import build_graph, run_gtm_agent
from .state import GTMState

__all__ = ["build_graph", "run_gtm_agent", "GTMState"]
