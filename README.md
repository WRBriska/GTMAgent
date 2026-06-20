# Go To Market (GTM) Agent

A self-contained **LangGraph + Claude** agent that runs a go-to-market workflow
end-to-end:

```
research → qualify → (discovery ↔ qualify, bounded loop) → recommend
```

Given a lead, it researches the account, scores it against an Ideal Customer
Profile, runs discovery to close information gaps (re-qualifying as it learns),
and produces a prioritized next-best-action with a drafted outreach message.

All external systems — CRM, firmographic enrichment, buying-signal feeds, call
transcripts — are **mocked**, so the agent runs anywhere with only an Anthropic
API key. The code is structured to swap those mocks for real integrations.

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # or copy .env.example → .env

python main.py                              # default sample lead (Northwind Logistics)
python main.py --company "BrightWave Health"
python main.py --company "TinyFox Studio"   # gets disqualified — small/no budget
python main.py --list                       # show built-in sample accounts
```

Any company name works; unknown names run against thin synthesized data so
qualification reflects genuine uncertainty.

## Architecture

| File | Responsibility |
|------|----------------|
| [gtm_agent/graph.py](gtm_agent/graph.py) | Compiles the `StateGraph`, wires conditional edges + the discovery loop, exposes `run_gtm_agent()` |
| [gtm_agent/state.py](gtm_agent/state.py) | `GTMState` typed channels (append reducer on `log`) |
| [gtm_agent/nodes.py](gtm_agent/nodes.py) | The four nodes: research, qualify, discovery, recommend |
| [gtm_agent/schemas.py](gtm_agent/schemas.py) | JSON Schemas for Claude structured outputs |
| [gtm_agent/llm.py](gtm_agent/llm.py) | Structured Claude call (`output_config.format`) with a tolerant fallback |
| [gtm_agent/prompts.py](gtm_agent/prompts.py) | Per-node system prompts + the editable ICP definition |
| [gtm_agent/tools.py](gtm_agent/tools.py) | Tool seam over the data sources (reimplement to go live) |
| [gtm_agent/mock_data.py](gtm_agent/mock_data.py) | Fabricated sample accounts |
| [main.py](main.py) | CLI demo + report formatting |

### The graph

- **research** — calls `enrich_account` + `search_buying_signals` + `get_crm_record`,
  then has Claude distill a factual brief.
- **qualify** — scores fit + intent against the ICP and returns
  `qualified` / `needs_discovery` / `disqualified`.
- **discovery** — answers the qualifier's `missing_info` from call transcripts,
  accumulates captured answers, lists what's still open, then loops back to
  **qualify** (bounded by `MAX_DISCOVERY_ROUNDS`).
- **recommend** — produces the next-best-action, channel, and a drafted,
  personalized outreach message.

Conditional routing after `qualify`:

- `disqualified` → `END`
- `qualified` → `recommend`
- `needs_discovery` → `discovery` (or `recommend` once the discovery budget is spent)

State is checkpointed with an in-memory saver, scoped by `thread_id`, so a run
can be resumed in-process.

## Using it as a library

```python
from gtm_agent import run_gtm_agent

state = run_gtm_agent(
    {"company": "Northwind Logistics", "contact_name": "Jordan Rivera", "title": "Director of RevOps"},
    thread_id="acct-123",
)
print(state["qualification"]["status"])
print(state["recommendation"]["next_best_action"])
```

## Prompt-injection defense

Everything the agent reads from outside — CRM notes, call transcripts,
enrichment, buying signals, and the lead's own fields — is attacker-influenceable
and gets re-injected into prompts. Two layers defend against that
([gtm_agent/security.py](gtm_agent/security.py)):

1. **Boundary sanitizer** — strips chat-template/control tokens (`<|im_start|>`,
   `[INST]`, spoofed `</untrusted_data>` / `system:` tags) and neutralizes explicit
   override phrases ("ignore previous instructions", "act as…", "new
   instructions:") from all untrusted strings. Applied to every tool output
   ([tools.py](gtm_agent/tools.py)) and to the lead at graph entry
   ([nodes.py](gtm_agent/nodes.py)); flagged events surface in the run log.
2. **Prompt isolation** — untrusted content is fenced in `<untrusted_data>` tags
   and every system prompt carries a directive
   ([prompts.py](gtm_agent/prompts.py)) telling the model to treat fenced content
   as data only — never instructions that can change the task, scores, verdict,
   or outreach recipients.

This is defense-in-depth, not a guarantee. For higher assurance, also constrain
*outputs* at the boundary (e.g. validate `outreach_*` recipients/links against an
allowlist before sending).

## Going to production

1. Reimplement the four functions in [gtm_agent/tools.py](gtm_agent/tools.py)
   against your real CRM / enrichment / intent / call systems — the nodes and
   graph stay unchanged.
2. Edit the ICP and prompts in [gtm_agent/prompts.py](gtm_agent/prompts.py).
3. Swap `MemorySaver` for a durable checkpointer (e.g. Postgres) in
   [gtm_agent/graph.py](gtm_agent/graph.py).

## Model

Defaults to `claude-opus-4-8`. Override with `GTM_MODEL` (e.g.
`claude-sonnet-4-6` for lower cost/latency). No sampling parameters are sent, as
Opus 4.8 rejects them.
