# EquiTie Investor Assistant

A personalised, **grounded** AI assistant that answers an EquiTie investor's questions
about their own portfolio — holdings, current value, MOIC, fees, capital calls,
distributions and account statement — citing the dataset rows behind every number.

> Report date is **2026-06-25** (treated as "today" for any upcoming/current figure).
> Everything is computed from the provided synthetic dataset in [`data/`](data/).

https://github.com/user-attachments/assets/90976f4e-ef29-4c3a-a8f0-818288bcc1c5

## Architecture

The design quarantines the numbers from the model:

- **Deterministic compute engine** (`backend/app/metrics.py`) is the single source of
  truth for every figure: FX-via-USD, current value, MOIC, DPI/RVPI, effective-vs-standard
  fees, upcoming/overdue obligations, carry, the account statement, and multi-round
  aggregation. **The LLM never does arithmetic.**
- **FastAPI backend** (`backend/`) loads the 10 CSVs into pandas once at startup and serves
  the engine. Investor isolation is enforced in the data layer — never by the model.
- **Claude via tool-use** (Sonnet 4.6 by default; swappable to Haiku 4.5 for cost or Opus 4.8 for
  the best answers) narrates the engine's results, personalised to the investor (tech-savviness, age,
  deal count, top sectors), citing the rows behind every figure. The model never sees another
  investor's data — tools are bound server-side to the active investor. Needs an Anthropic API key.
- **Nuxt 3 + TypeScript + Tailwind + ECharts** frontend: investor picker, dashboard, and a
  streaming chat panel, in an "equitie" black/blue theme with light/dark. *Phase 3.*

## Layout

```
backend/   FastAPI app + deterministic engine + tests
frontend/  Nuxt 3 app — investor picker, dashboard, charts, streaming chat
data/      the provided CSV dataset (10 files)
.github/workflows/ci.yml   CI: backend (ruff + pytest) and frontend (eslint + vue-tsc + vitest + build)
```

## Run the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Then: `GET /api/health`, `GET /api/investors`, `GET /api/portfolio/INV001`, and
`POST /api/chat/INV001` (SSE streaming). The chat endpoint needs an Anthropic key —
copy `backend/.env.example` to `backend/.env` and set `ANTHROPIC_API_KEY`.

## Run the frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000  (expects the backend on :8000)
```

Launch screen is the investor picker (no auth). The dashboard is a single-screen, Bloomberg-dense
layout: KPI tiles, ECharts, an expandable streaming chat panel, and a click-to-expand holdings
table — each panel has a maximise button for focus mode. Tone/depth adapt to the investor's
tech-savviness, with extra inline explanations for less-technical investors. Black/blue "equitie"
theme with a light/dark toggle.

**Mobile / iOS:** the layout is responsive down to phones (the two charts are hidden on small
screens to keep the focus on numbers and chat). The production target is the EquiTie **iOS app** —
this web app is the prototype surface for the same flow.

**Chat persistence:** conversations are kept per investor in `localStorage`, so a refresh keeps the
thread. This is a deliberate client-only stopgap — server-side/DB persistence is on the roadmap.

## Tests

```bash
# Backend
cd backend && pip install -r requirements.txt -r requirements-dev.txt && ruff check . && pytest

# Frontend
cd frontend && npm install && npm run lint && npm run typecheck && npm run test
```

The golden tests hand-verify the core metrics against the raw rows, and the edge-case
tests cover every "trap" in the dataset: same company across multiple rounds, per-allocation
share-price discounts, multi-currency, commitment vs contributed, pending/zero-holdings
investors, exits, write-offs, down rounds, similar company names, partial secondaries,
overdue fees, and the USD admin fee on non-USD deals.

## Status

- [x] **Phase 0** — scaffold + data spine
- [x] **Phase 1** — deterministic compute engine + golden tests
- [x] **Phase 2** — Claude tool layer + SSE chat (Haiku 4.5, tool-use, citations)
- [x] **Phase 3** — Nuxt dashboard (investor picker, KPIs, ECharts, streaming chat, theming)
- [x] **Phase 4** — hardening + `ai-workflow.md` + 6-month build roadmap

## Deliverables

- [`ai-workflow.md`](ai-workflow.md) — AI tooling and models, % AI-generated, what was changed and why, how answers were verified.
- [`ROADMAP.md`](ROADMAP.md) — the 6-month plan for the full iOS relationship-manager bot.

## Assumptions

- The investor is already authenticated; the picker stands in for login (per the brief).
- Report date is fixed at **2026-06-25** ("today").
- **MOIC = (current value + distributions net of carry) / contributed**, per the dataset guide;
  carry comes from the data's `net_amount` (charged on the gain, not on gross proceeds).
- Current value = latest mark × units × live fraction, and is **0** for exited/written-off deals;
  **pending (unfunded) allocations are excluded** from deployed value/MOIC and shown as outstanding
  commitments.
- DPI/RVPI and portfolio MOIC use **net** distributions over **contributed** capital.
- FX uses the report-date `to_usd` rates, always via USD; the admin fee is in USD even on non-USD
  deals (each row's own currency is used for conversion).
- Narration runs on **Claude Haiku 4.5** by default; swap via `ANTHROPIC_MODEL`.

## Known limitations & failure modes

- **Chat needs a key.** Without `ANTHROPIC_API_KEY`, `/api/chat` returns a clear 503 and the UI says
  so. The dashboard, engine and all tests run without a key.
- **Personalisation quality rides on a small model.** Haiku + pure system-prompt steering is the
  weakest link for tone nuance — never for numbers, which are deterministic. One env var bumps
  narration to Sonnet 4.6 / Opus 4.8.
- **Prompt-injection not yet red-teamed.** Investor isolation is enforced server-side (tools are
  bound to the active investor), so "show me another investor" cannot leak data — but adversarial
  prompting of the narration layer is future work.
- **Dashboard reads `/api/portfolio` only.** Obligations, fees and the statement are answerable in
  chat but not yet surfaced as dashboard tiles.
- **Data is loaded in-memory at startup** — ideal for ~5k rows, not a large-data/streaming design.
- **Chat persistence is client-side only.** History is kept per investor in `localStorage` so a
  refresh keeps the thread, and is sent to the backend per request — there is no server-side/DB
  conversation store yet (on the roadmap).
