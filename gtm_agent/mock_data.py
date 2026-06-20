"""Mocked external data sources.

Stands in for a CRM, a firmographic-enrichment provider, a buying-signal/intent
feed, and a call-recording/transcript system. Everything here is fabricated and
deterministic so the agent runs with no credentials beyond an Anthropic key.

Swap these dicts for real integrations (e.g. Salesforce, Clearbit, a call
platform) by reimplementing the functions in :mod:`gtm_agent.tools`.
"""

from __future__ import annotations

from typing import Any

# Keyed by a normalized identifier (lowercase company name or domain stem).
_ACCOUNTS: dict[str, dict[str, Any]] = {
    "northwind": {
        "company": "Northwind Logistics",
        "domain": "northwind.example",
        "firmographics": {
            "industry": "Freight & supply-chain logistics",
            "employees": 2400,
            "annual_revenue_usd": 480_000_000,
            "hq": "Columbus, OH, USA",
            "tech_stack": ["SAP ERP", "Manhattan WMS", "Snowflake"],
        },
        "signals": [
            "Posted 6 open roles for 'Revenue Operations' and 'Data Engineer' in the last 30 days",
            "CFO quoted in a trade publication about 'modernizing the order-to-cash stack'",
            "Visited pricing page 11 times in two weeks (3 distinct users)",
            "Expanded into two new distribution regions last quarter",
        ],
        "crm": {
            "stage": "Open - working",
            "owner": "Jordan Lee (AE)",
            "first_touch": "Inbound demo request",
            "last_activity": "Discovery call held 4 days ago",
            "notes": "Champion in RevOps; budget owner is the CFO. Competitive eval underway.",
        },
        "transcripts": [
            {
                "date": "2026-06-15",
                "snippet": (
                    "RevOps lead: We're drowning in manual order reconciliation across three "
                    "regional systems. We need this live before our Q4 peak season. Budget is "
                    "approved at the CFO level — roughly $150-200k for year one. The main blocker "
                    "is that our SAP data is messy and we'd need help with the migration."
                ),
            },
            {
                "date": "2026-06-15",
                "snippet": (
                    "AE: Who else needs to sign off? RevOps lead: IT security has to approve any "
                    "vendor that touches order data, and the CFO makes the final call. We are also "
                    "looking at one competitor, but we prefer a partner who can own the data cleanup."
                ),
            },
        ],
    },
    "brightwave": {
        "company": "BrightWave Health",
        "domain": "brightwave.example",
        "firmographics": {
            "industry": "Healthcare SaaS",
            "employees": 180,
            "annual_revenue_usd": 28_000_000,
            "hq": "Austin, TX, USA",
            "tech_stack": ["NetSuite", "HubSpot", "AWS"],
        },
        "signals": [
            "Downloaded a whitepaper but no repeat site visits",
            "Series B raised 14 months ago",
        ],
        "crm": {
            "stage": "Open - nurturing",
            "owner": "Priya Shah (AE)",
            "first_touch": "Webinar registration",
            "last_activity": "No reply to last 2 emails",
            "notes": "Early interest from a manager-level contact; no budget confirmed.",
        },
        "transcripts": [
            {
                "date": "2026-05-02",
                "snippet": (
                    "Manager: We're just exploring for now. No active project or budget this year — "
                    "maybe something to revisit in a couple of quarters. Compliance is strict given "
                    "we handle patient data."
                ),
            }
        ],
    },
    "tinyfox": {
        "company": "TinyFox Studio",
        "domain": "tinyfox.example",
        "firmographics": {
            "industry": "Indie game studio",
            "employees": 7,
            "annual_revenue_usd": 600_000,
            "hq": "Remote",
            "tech_stack": ["Notion", "Stripe"],
        },
        "signals": ["Signed up for a free trial with a personal email"],
        "crm": {
            "stage": "Open - new",
            "owner": "Unassigned",
            "first_touch": "Free trial signup",
            "last_activity": "Trial signup today",
            "notes": "Very small team; likely below our minimum deal size.",
        },
        "transcripts": [],
    },
}


def _normalize(identifier: str) -> str:
    """Reduce a company name or domain to a lookup key."""
    text = str(identifier or "").strip().lower()
    if not text:
        return ""
    # domain → stem (northwind.example → northwind)
    if "." in text:
        text = text.split("//")[-1].split("/")[0]
        text = text.split(".")[0]
    # company name → first word ("Northwind Logistics" → northwind)
    return text.split()[0] if text else ""


def lookup(identifier: str) -> dict[str, Any] | None:
    """Return the raw account record for an identifier, or None."""
    return _ACCOUNTS.get(_normalize(identifier))


def known_accounts() -> list[str]:
    """Company names available in the mock dataset (for the CLI help)."""
    return [record["company"] for record in _ACCOUNTS.values()]


def synthesize(identifier: str) -> dict[str, Any]:
    """Fabricate a minimal record for an unknown account.

    Lets the agent run end-to-end on any input without erroring; the data is
    deliberately thin so qualification reflects genuine uncertainty.
    """
    name = str(identifier or "Unknown Account").strip() or "Unknown Account"
    return {
        "company": name,
        "domain": _normalize(name) + ".example",
        "firmographics": {
            "industry": "Unknown",
            "employees": None,
            "annual_revenue_usd": None,
            "hq": "Unknown",
            "tech_stack": [],
        },
        "signals": [],
        "crm": {
            "stage": "Open - new",
            "owner": "Unassigned",
            "first_touch": "Unknown",
            "last_activity": "None recorded",
            "notes": "No enrichment data available for this account.",
        },
        "transcripts": [],
    }
