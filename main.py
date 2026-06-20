"""CLI demo for the Go To Market agent.

Examples
--------
    python main.py                          # run the default sample lead
    python main.py --company "Northwind Logistics"
    python main.py --company "BrightWave Health" --contact "Dana Cole" --title "VP Ops"
    python main.py --list                   # show the built-in sample accounts

Requires only ``ANTHROPIC_API_KEY`` in the environment (or a .env file).
"""

from __future__ import annotations

import argparse
import sys

from gtm_agent import config, mock_data
from gtm_agent.graph import build_graph, run_gtm_agent

# Render Unicode glyphs correctly on legacy Windows console codepages.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

_RULE = "─" * 72


def _print_section(title: str) -> None:
    print(f"\n{_RULE}\n{title}\n{_RULE}")


def _print_result(state: dict) -> None:
    lead = state.get("lead", {})
    research = state.get("research", {})
    qual = state.get("qualification", {})
    disc = state.get("discovery", {})
    rec = state.get("recommendation", {})

    _print_section(f"GTM AGENT REPORT — {lead.get('company', 'Unknown')}")

    print("\n[Research]")
    print(f"  Industry : {research.get('industry', '?')}")
    print(f"  Size     : {research.get('estimated_size', '?')}")
    print(f"  Overview : {research.get('company_overview', '')}")
    for signal in research.get("buying_signals", []):
        print(f"   • signal: {signal}")

    print("\n[Qualification]")
    print(f"  Status   : {qual.get('status', '?')}")
    print(f"  Fit      : {qual.get('fit_score', '?')}/100   Intent: {qual.get('intent_score', '?')}/100")
    print(f"  Rationale: {qual.get('rationale', '')}")

    if disc:
        print("\n[Discovery]")
        print(f"  {disc.get('summary', '')}")
        for item in disc.get("captured", []):
            print(f"   ✓ {item.get('question')} → {item.get('answer')}")
        for q in disc.get("open_questions", []):
            print(f"   ? open: {q}")

    if rec:
        print("\n[Recommendation]")
        print(f"  Priority : {rec.get('priority', '?')}")
        print(f"  Action   : {rec.get('next_best_action', '')}")
        print(f"  Channel  : {rec.get('outreach_channel', '')}")
        print(f"\n  Draft outreach — Subject: {rec.get('outreach_subject', '')}")
        print("  " + "\n  ".join(rec.get("outreach_body", "").splitlines()))
        if rec.get("talking_points"):
            print("\n  Talking points:")
            for point in rec["talking_points"]:
                print(f"   • {point}")
    else:
        print("\n[Recommendation]")
        print("  None — account was disqualified.")

    _print_section("RUN LOG")
    for line in state.get("log", []):
        print(f"  · {line}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Go To Market agent on a lead.")
    parser.add_argument("--company", default="Northwind Logistics", help="Company name or domain.")
    parser.add_argument("--contact", default="Jordan Rivera", help="Contact full name.")
    parser.add_argument("--title", default="Director of RevOps", help="Contact job title.")
    parser.add_argument("--source", default="Inbound demo request", help="Lead source.")
    parser.add_argument("--thread-id", default="cli-demo", help="Checkpointer thread id.")
    parser.add_argument("--list", action="store_true", help="List built-in sample accounts and exit.")
    args = parser.parse_args(argv)

    if args.list:
        print("Built-in sample accounts:")
        for name in mock_data.known_accounts():
            print(f"  • {name}")
        print("(Any other name runs against synthesized, thin data.)")
        return 0

    if not config.has_api_key():
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. Export it or add it to a .env file.",
            file=sys.stderr,
        )
        return 1

    lead = {
        "company": args.company,
        "contact_name": args.contact,
        "title": args.title,
        "source": args.source,
    }

    print(f"Running GTM agent on '{args.company}' (model={config.get_model()})…")
    graph = build_graph()
    final_state = run_gtm_agent(lead, thread_id=args.thread_id, graph=graph)
    _print_result(final_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
