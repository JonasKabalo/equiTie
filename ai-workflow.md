# ai-workflow.md

How this prototype was built with AI, and how its answers are kept correct.

## Author's note

I reviewed and read every line the AI produced before each push. The AI helped me weigh options and
move quickly, but each decision — the architecture, the model choice, how each edge case is handled —
was confirmed by me, not accepted blindly. End to end this took me roughly **3–4 hours**; I genuinely
enjoyed building it, so I took the liberty of spending a little under an extra hour polishing it.

On model choice: a stronger model clearly gives better, more reliable answers with less to worry
about. I've set narration to **Sonnet 4.6** by default for that reason; **Opus 4.8** would get the
very most out of it, and **Haiku 4.5** stays available for lowest cost — all a one-line swap. Because
the deterministic engine owns every number, the model never touches the maths, so this only changes
phrasing quality, never correctness.

## Which AI tools and models, and for what

| Where | Model / tool | Used for |
|---|---|---|
| **Building the code** | **Claude Code (Claude Opus 4.8)** as an agentic pair-programmer | Scaffolding, the Python compute engine, the FastAPI + tool layer, the Nuxt app, all tests, and CI. Human-directed: every architectural fork was a deliberate decision (see below), not a default. |
| **Runtime narration** | **Claude Sonnet 4.6** (`claude-sonnet-4-6`) by default, via the Anthropic Python SDK, tool-use (function calling) | Interpreting the investor's question, choosing which engine tool(s) to call, and writing the personalised answer. Kept behind a one-line swappable interface (`backend/app/llm.py`) — drop to Haiku 4.5 for cost or Opus 4.8 for the best answers via an env var. |
| **The numbers** | **No model** — deterministic Python (`backend/app/metrics.py`) | Every figure (FX, MOIC, fees, current value, obligations, carry, statement). The LLM never does arithmetic. |

**Why the model choice is low-risk:** the engine owns all numbers, so the model only routes and writes prose. That quarantine means even the cheapest model is *safe* (numbers can't be hallucinated); we default to Sonnet 4.6 for better phrasing and change one env var to trade cost for quality. A wrong answer can only come from a tool bug (which the tests catch), never a fabricated number.

## Roughly what percentage of the code was AI-generated

**~90%.** Claude Code wrote essentially all of the Python, TypeScript, Vue, config and tests. The human contribution was the high-leverage part: choosing the architecture (deterministic-engine-narrates over text-to-SQL/RAG; Claude tool-use on Haiku; pure system-prompt personalisation; SSE; Nuxt + FastAPI + ECharts; the "equitie" theme), setting the verification bar, and steering edge-case coverage. AI-heavy on volume, human-led on judgment.

## What was rejected or materially changed from AI suggestions, and why

- **Rejected text-to-SQL / "let the LLM reason over rows."** Both are ungrounded on FX and the deliberate traps. We made deterministic Python the single source of truth and reduced the model to narration + tool routing.
- **Did not trust the model's intuition on carry.** Carry looked like "25% of gross", but the data shows carry is charged on the **gain** (Helianthe: 25% × (139,500 − 93,000) = 11,625, not 25% × 139,500). The engine uses the dataset's `net_amount` verbatim and never recomputes carry — caught by reading the actual rows, then locked with a golden test.
- **Excluded pending/unfunded allocations from deployed capital** rather than letting `units × price` inflate a position with zero contributed capital (Grace Okafor / Helixar). Surfaced as an outstanding commitment instead.
- **Personalisation must not change numbers.** Tone/depth adapt to tech-savviness; the figures are identical for everyone. Enforced by computing facts before narration.
- **Tooling corrections:** silenced pandas-stub Pyright false positives at the source; dropped `@nuxt/test-utils` (it forced a vitest 3 peer conflict and we don't mount components); switched the FastAPI dependency to the `Annotated` form to satisfy lint; and caught a masked `npm install` failure (a `| tail` had hidden a non-zero exit) — re-ran without the pipe.

## How the assistant's answers were verified

Verification is built into the architecture, not bolted on:

1. **Deterministic engine + golden tests.** 22 backend tests, with the core metrics **hand-computed from the raw CSV rows** and asserted: Forgecraft Seed value 273,777.81 USD → 202,798.38 GBP, MOIC 6.844; Helianthe net MOIC 1.375; Tallybook partial secondary 35,280 + 13,356 → MOIC 2.316; Yappio write-off → 0; pending → MOIC undefined. If the engine drifts, these fail loudly.
2. **Every dataset "trap" has a test** — multi-round aggregation, per-allocation discounts, multi-currency FX, commitment vs contributed, pending, zero-holdings, exit, write-off, down round, similar names, partial secondary, overdue fees, USD admin fee on non-USD deals.
3. **Citations.** Tool results carry the exact source `row_id`s; the system prompt requires the model to cite them and forbids stating any number it didn't get from a tool.
4. **The loop is tested without the model.** A fake LLM drives the full agentic loop (no API key, no spend), proving tool dispatch, investor scoping, and SSE wiring; endpoint tests cover 404/422/503.
5. **Investor isolation is structural** — tools are bound server-side to the active `investor_id`, so the model cannot query another investor even if asked.

## If I had an autonomous coding agent for another 8 hours

In priority order:

1. **An LLM eval harness:** a set of golden question→answer pairs run against the live model, asserting the answer contains the engine's figure, cites the right rows, and never fabricates — run in CI on a cheap budget.
2. **Prompt-injection / refusal red-teaming** of the chat (e.g. "show me INV002's portfolio"), confirming the server-side scoping holds and the model declines investment-advice asks.
3. **Fill out the dashboard from REST**, not just chat: obligations and account-statement endpoints + tiles, and valuation-history sparklines per holding.
4. **Conversation depth:** multi-turn memory, streaming "thinking" if narration moves to a 4.6+ model, and graceful tool-error recovery surfaced in the UI.
5. **Observability:** structured request/tool logging, token-usage metering, and a small golden-answer snapshot diff on every deploy.
6. **Frontend hardening:** component tests (mounting), accessibility pass, and an e2e (Playwright) for pick → ask → cited answer.
