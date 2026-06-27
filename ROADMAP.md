# Build Roadmap — EquiTie Investor Assistant → Relationship-Manager Bot

Six months, a well-resourced team, shipping inside the EquiTie iOS investor app. The goal is a
bot that does much of what a human relationship manager (RM) does today — not just answer
questions — while keeping a human firmly in the loop for anything that moves money, makes a
commitment, or could be read as advice.

The prototype in this repo is the spine of Phase 1: a deterministic compute engine that owns every
number, with the LLM grounded to it via tools and citations. Everything below extends that
principle rather than replacing it.

---

## 1. Scope and capabilities

**Tier 1 — Grounded Q&A (the prototype, hardened).** Portfolio, positions, fees, valuations,
distributions, obligations, statement — every figure cited to source rows, personalised to the
investor. This is the trust foundation; nothing else ships until it is provably correct.

**Tier 2 — Proactive RM (the real product).**
- **Nudges & reminders:** upcoming/overdue capital calls and management fees, KYC expiry, new
  marks on holdings, distribution notices — push notifications with a one-tap drill-in.
- **Document & KYC workflows:** request and collect KYC/AML documents, route to e-signature for
  subscription docs and side letters, track status, chase missing items.
- **Onboarding:** guide a new investor from invite → KYC → first commitment, answering questions
  in-flow.
- **Reporting:** generate the quarterly statement and a plain-language portfolio summary on demand
  or on schedule.
- **Drafting investor comms (human-approved):** draft the RM's replies and update emails; the RM
  reviews and sends. The bot drafts; a human signs.

**Stays with a human (hard boundary).**
- Any **investment advice** (buy/sell/hold, suitability) — the bot explains data, never recommends.
- **Irreversible or money-moving actions** — approving a wire, finalising an allocation, binding the
  fund — are bot-*prepared*, human-*approved*.
- **Exceptions, disputes, relationship judgement, and anything legal/regulated** escalate to the RM
  with full context attached.

Design rule: the bot can **read** freely and **draft** anything, but **write actions are gated**
behind either deterministic rules or human approval, scaled to reversibility.

---

## 2. Architecture and tech stack

```
iOS app (SwiftUI) ──HTTPS/SSE──► API gateway ──► Orchestrator (agent loop)
                                                   │   ├─ tools → Deterministic Services
                                                   │   │         (portfolio, fees, obligations,
                                                   │   │          statement) — own all numbers
                                                   │   ├─ retrieval → docs/policy (RAG)
                                                   │   └─ model → Claude (tiered)
                                                   ├─ Integrations layer (ledger, fund admin,
                                                   │   CRM, KYC, e-sign, comms, market data)
                                                   ├─ Eval + Observability
                                                   └─ Audit log (append-only)
```

- **Client:** native **SwiftUI** in the existing iOS app; streaming chat over SSE; push via APNs.
- **Backend:** **Python (FastAPI)** for the AI/orchestration services (matches the prototype and the
  data/ML ecosystem); existing platform services stay where they are and are exposed as tools.
- **Data layer:** the **portfolio ledger remains the system of record**. We add a read-optimised
  query layer (Postgres + a typed repository, the prototype's engine grown up) and a **vector store**
  (pgvector) for documents/policy. No financial figure is ever embedding-retrieved — only documents.
  **Conversations are persisted server-side** (Postgres) with per-user history and audit — the
  prototype's `localStorage` chat is a deliberate stopgap to be replaced here.
- **Orchestration:** a code-controlled agent loop (own the loop, don't hand control to the model) with
  tool-use; deterministic services for all math, RAG only for unstructured text.
- **Model choice & hosting:** **Claude**, tiered — Haiku 4.5 for routing/classification and simple
  Q&A, Sonnet 4.6 for the main RM reasoning and drafting, Opus 4.8 for the hardest synthesis. Hosted
  via the Anthropic API, with **Claude on AWS / Bedrock** as the enterprise path for data-residency
  and procurement. Prompt caching on the stable system prompt + schema.
- **Evaluation & observability:** a golden-answer eval suite in CI; per-request tracing, token
  metering, tool-call logs, and a quality dashboard.
- **Security:** SSO/auth from the existing app; per-investor data scoping enforced in the data layer
  (never by the model); secrets server-side; append-only audit log of every tool call and draft.

---

## 3. Data and integrations

| System | Direction | Use |
|---|---|---|
| **Portfolio ledger** (system of record) | read | positions, valuations, cashflows — the numbers |
| **Fund administration** | read / write-prepare | capital calls, distributions, NAV; bot prepares notices |
| **CRM** (e.g. Salesforce/HubSpot) | read / write | investor profile, RM ownership, interaction history, tasks |
| **KYC/AML provider** | read / write | identity checks, document requests, status |
| **E-signature** (e.g. DocuSign) | write-prepare | subscription docs, side letters — sent for human/investor signature |
| **Comms** (email/push/APNs) | write-prepare | reminders and drafts; sends gated by rules or approval |
| **Valuation / market data** | read | marks and reference data feeding the ledger |

Data flow: integrations sync into the read layer on a schedule/webhook; the orchestrator's tools read
from there (fast, consistent, auditable) and **write back only through the integration layer**, never
directly, so every external action is logged and reversible-where-possible. PII is minimised in
prompts; the model sees computed facts and document snippets, not raw tables.

---

## 4. AI approach and safety

- **Grounding:** deterministic services compute every figure and return facts + citations; RAG serves
  only documents/policy. The model's job is to choose tools, synthesise, and write — the same pattern
  as the prototype.
- **Where deterministic code wins:** all arithmetic, all eligibility/threshold logic, all
  money-moving steps, and reminder triggers (a fee is due because a date passed, not because a model
  thinks so).
- **Tool use & gating:** read tools are free; write tools (send comms, request docs, prepare a wire)
  require either a deterministic rule or human approval, sized to reversibility.
- **Evaluation:** golden Q&A + drafting evals run in CI; an LLM-as-judge plus human spot-checks on a
  sampled live traffic; regression gates before each release.
- **Guardrails & compliance:** **no investment advice** (refuse/redirect, tested); per-investor data
  isolation enforced in code; **append-only audit trail** of prompts, tool calls, drafts and approvals;
  data-protection by design (minimised PII, retention controls, region-pinned hosting); prompt-injection
  defence (the model never holds the auth boundary; untrusted document text is treated as data).

---

## 5. Team and hiring

| Role | Seniority | Headcount | Lands |
|---|---|---|---|
| Tech lead / AI engineer | Senior/Staff | 1 | Month 0 |
| Backend / AI engineers | Mid–Senior | 2 | Month 0–1 |
| iOS engineer | Senior | 1 | Month 1 |
| Data / integrations engineer | Senior | 1 | Month 1 |
| ML/eval engineer | Mid–Senior | 1 | Month 2 |
| Product manager | Senior | 1 (shared) | Month 0 |
| Designer | — | 0.5 (shared) | Month 1 |
| Compliance / legal partner | — | 0.5 (advisory) | Month 0, ongoing |

Peak ≈ **6–7 engineers** plus shared PM/design and a compliance partner. Start lean (lead + 2 backend)
to nail the grounded core; add iOS/data/eval as the surface grows.

---

## 6. Timeline (phased)

- **Month 1 — Grounded core, productionised.** Harden the prototype: full engine coverage, eval
  harness in CI, observability, auth + per-investor scoping, audit log. *Ships: trustworthy in-app Q&A.*
- **Month 2 — Integrations read-path.** Ledger/fund-admin/CRM read connectors into the read layer;
  document RAG for policy/FAQ. *Ships: answers that span live ops data + documents.*
- **Month 3 — Proactive read-only.** Nudges and reminders (capital calls, fees, KYC expiry, new marks)
  via push; on-demand reporting. *Ships: the bot reaches out, no write actions yet.*
- **Month 4 — Human-approved writes.** Draft investor comms and KYC/document requests with an RM
  approval queue; e-signature prep. *Ships: bot drafts, humans approve and send.*
- **Month 5 — Onboarding + guarded automation.** Guided onboarding; auto-send the lowest-risk,
  rule-bounded reminders without per-message approval. *Ships: end-to-end onboarding assist.*
- **Month 6 — Scale, evaluate, harden.** Red-teaming, load and cost tuning, compliance sign-off, model
  tiering optimisation, broaden rollout. *Ships: GA to all investors.*

Milestone gate every month: the eval suite and a compliance review must pass before the next surface
opens.

---

## 7. Risks and cost

**Main risks & mitigations**
- *Wrong numbers / hallucination* → deterministic engine + citations + golden evals; the model can't
  invent figures. **Highest-priority risk, structurally mitigated.**
- *Acting like a financial adviser* → hard guardrail + tests + compliance review; bot explains, never
  advises.
- *Unauthorised data exposure* → scoping in the data layer, not the model; audit everything.
- *A wrong write action* → reversibility-scaled gating; money-moving stays human-approved.
- *Integration fragility / bad upstream data* → read layer with validation and "stale data" surfacing;
  fail closed.

**Build vs buy**
- **Buy:** foundation models (Anthropic), KYC/AML, e-signature, CRM, push, vector store — undifferentiated.
- **Build:** the deterministic compute engine, the orchestration + tool layer, the eval harness, and
  the gating/audit logic — this is the moat and the trust surface, and must not be a black box.

**Rough cost shape (monthly, at steady state)**
- *People* dominate: ~6–7 engineers + shared PM/design/compliance — the large majority of spend.
- *Inference* is modest and controllable: tiered models (Haiku-first), prompt caching, and
  deterministic short-circuiting keep per-investor cost low — likely **low-thousands $/month** at the
  112-investor scale, scaling sub-linearly with caching.
- *Infra + third-party SaaS* (hosting, KYC, e-sign, CRM seats) a secondary, predictable line.

The economics are people-led, not token-led — which is the right shape: the value and the risk both
live in the engineering and the guardrails, not the model bill.

---

## 8. Author's notes — choices, trade-offs and what I'd do for production on top of what have been written

Everything in this submission was reviewed and read by me before pushing. The AI helped me choose
between options and move fast, but I confirmed every decision.

- **Packaging & DX.** For a production push I'd ship with **Docker**, and put the repo behind a
  **Turborepo** monorepo so the team can run and build the apps faster.
- **Model, with unlimited budget.** A vendor model (Claude) is the right way to start. With truly
  unlimited investment, an **in-house LLM built by our own engineers** could win on cost at scale and
  be strengthened over time — it's increasingly practical to build today, and owning it lowers the
  long-run per-answer cost.
- **Frontend framework.** I used **Nuxt** here; for this product I might instead reach for **plain
  Vue**. I would not use React — it tends to mean more code and more re-rendering for the same
  result, which isn't what we want for a dense, focused dashboard.
- **Backend & data.** Stay on **Python**, with a managed **PostgreSQL on AWS**.
- **API for iOS.** I'd add a **GraphQL** server for the iOS app — GraphQL scales elegantly for large
  applications (it powers products like Facebook) and lets the client fetch exactly what it needs.
- **Ship to users first.** Before going live I'd put the product in front of a **handful of real
  users**, monitor how they actually use it, and ask them what to improve. The **user experience**
  matters as much as accurate AI answers — a good assistant that is awkward to use still fails.
