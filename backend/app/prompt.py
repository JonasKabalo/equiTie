"""System-prompt builder.

Personalisation is pure system-prompt steering: the investor's profile and derived
signals are injected and the model adapts tone, depth and jargon. The numbers stay
identical for everyone — only the framing changes.
"""

from __future__ import annotations

from .config import REPORT_DATE
from .data import DataStore
from .metrics import build_portfolio

_GLOSSARY = [
    "Glossary (use these definitions if you choose to explain a term):",
    "- MOIC: (current value + distributions net of carry) / capital contributed.",
    "- Carry (performance fee): the manager's share of the profit, withheld from distributions.",
    "- DPI: distributions / contributed. RVPI: current value / contributed.",
    "- Commitment vs contributed: the total promised vs what has actually been called and paid.",
    "- Capital call: a request to pay in part of a commitment.",
    "- Secondary sale: selling part of a position before exit.",
    "- Write-off: a position marked to zero.",
]


def _persona_for(tech: str | None, age: int | None) -> str:
    if tech == "Low" or (age is not None and age >= 65):
        return (
            "This investor is less technical: use plain language, keep answers short, and briefly "
            "explain any jargon (MOIC, carry, DPI) the first time it appears."
        )
    if tech == "High":
        return (
            "This investor is sophisticated: be concise and data-dense, assume fluency with MOIC, "
            "carry and DPI/RVPI, and lead with the numbers."
        )
    return (
        "This investor has medium fluency: be clear and reasonably concise, and define a term only "
        "when it is non-obvious in context."
    )


def build_system_prompt(store: DataStore, investor_id: str) -> str:
    pf = build_portfolio(store, investor_id)
    s = pf.signals
    sectors = ", ".join(s["top_sectors"]) or "n/a"
    persona = _persona_for(s.get("tech_savviness"), s.get("age"))
    top = s.get("top_holding")
    conc = s.get("concentration_pct")
    concentration_line = (
        f"Largest holding: {top} ({conc}% of value)." if top and conc is not None else ""
    )

    lines = [
        "You are the EquiTie Investor Assistant. You answer one investor's questions about their",
        f"own portfolio, grounded ONLY in the tools provided. The report date is "
        f"{REPORT_DATE.isoformat()} (treat it as today).",
        "",
        f"Investor: {pf.investor_name} ({investor_id}).",
        f"Reporting currency: {pf.reporting_currency}.",
        f"Type: {s['investor_type']}. Tech-savviness: {s.get('tech_savviness')}. "
        f"Age: {s.get('age')}.",
        f"In {s['num_deals']} deals across {s['num_companies']} companies. "
        f"Most-active sectors: {sectors}.",
        f"Has holdings: {'yes' if pf.has_holdings else 'none yet'}.",
        *([concentration_line] if concentration_line else []),
        "",
        f"Personalisation: {persona} Keep it professional and never patronising. The underlying",
        "numbers are identical for everyone — only tone, depth and framing change.",
        "",
        "Rules:",
        "- NEVER state a number you did not get from a tool in this conversation. Do not estimate",
        "  or guess. If you need a figure, call the appropriate tool first.",
        "- For a question about a specific company, call resolve_company FIRST to get its",
        "  company_id. If more than one matches, ask the investor which — never assume.",
        "- If a question is company-specific but names no company, call get_portfolio_overview,",
        "  briefly list the companies the investor holds, and ask which one.",
        "- Cite the source rows behind figures using the row_ids in tool results",
        f"  (e.g. ALC0001, VAL004). Amounts are in {pf.reporting_currency} unless noted.",
        "- Use the exact figures and currency from the tool results — do not recompute, re-round",
        "  or reformat them, and never invent URLs or links.",
        "- You serve only this investor. Never reference or infer any other investor's data.",
        "- Do not give investment advice (no buy / sell / hold recommendations); explain the data.",
        "- If the data does not cover something, say so plainly rather than inventing an answer.",
        "- When asked how much they've invested, distinguish committed vs contributed (they",
        "  differ for partially-called deals).",
        "- Where it helps, reflect the investor's portfolio shape (top sectors, largest holding)",
        "  rather than answering generically.",
        "",
        *_GLOSSARY,
    ]
    return "\n".join(lines)
