"""Assemble and run the GTM ``StateGraph``.

Flow::

    START → research → qualify ─┬─ disqualified ──────────────→ END
                                ├─ needs_discovery → discovery ─┐
                                │        ▲                       │
                                │        └───────────────────────┘  (re-qualify, bounded)
                                └─ qualified ──────→ recommend → END

The discovery node loops back into qualify so the verdict is re-evaluated with
new information; ``MAX_DISCOVERY_ROUNDS`` caps the loop and falls through to
``recommend`` if discovery can't close the gaps.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import GTMState


def _route_after_qualify(state: GTMState) -> str:
    """Decide where to go after qualification."""
    status = state.get("qualification", {}).get("status", "needs_discovery")
    if status == "disqualified":
        return "end"
    if status == "qualified":
        return "recommend"
    # needs_discovery — but stop looping once the budget is spent.
    if state.get("discovery_rounds", 0) >= nodes.MAX_DISCOVERY_ROUNDS:
        return "recommend"
    return "discovery"


def build_graph(checkpointer: Any | None = None):
    """Compile and return the GTM agent graph.

    Pass a ``checkpointer`` to persist state across invocations; defaults to an
    in-memory saver so a thread can be resumed within the same process.
    """
    builder = StateGraph(GTMState)

    builder.add_node("research", nodes.research_node)
    builder.add_node("qualify", nodes.qualify_node)
    builder.add_node("discovery", nodes.discovery_node)
    builder.add_node("recommend", nodes.recommend_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "qualify")
    builder.add_conditional_edges(
        "qualify",
        _route_after_qualify,
        {"discovery": "discovery", "recommend": "recommend", "end": END},
    )
    builder.add_edge("discovery", "qualify")  # re-qualify with new info (bounded loop)
    builder.add_edge("recommend", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())


def run_gtm_agent(
    lead: dict[str, Any],
    *,
    thread_id: str = "default",
    graph: Any | None = None,
) -> GTMState:
    """Run a lead through the full pipeline and return the final state.

    ``thread_id`` scopes the checkpointer so repeated calls with the same id
    resume the same conversation/session.
    """
    graph = graph or build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"lead": lead}, config=config)
