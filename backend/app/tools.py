"""Claude tool layer.

Each tool wraps a deterministic engine function and returns facts + citation
row-ids. The ``investor_id`` is bound server-side by :func:`dispatch` — it is
never a tool parameter, so the model cannot ask about another investor.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass

from .data import DataStore
from .metrics import (
    account_statement,
    build_portfolio,
    fees_for_company,
    position_detail,
    realised_outcomes,
    resolve_company,
    upcoming_obligations,
    valuation_history,
)

# Tool schemas sent to the Anthropic API. Descriptions are prescriptive about
# *when* to call each tool (this materially improves tool selection).
TOOLS: list[dict] = [
    {
        "name": "get_portfolio_overview",
        "description": (
            "The investor's whole-portfolio summary in their reporting currency: holdings "
            "by company, total committed vs contributed, current value, blended MOIC, DPI/RVPI, "
            "top sectors and any pending (unfunded) commitments. Call this for 'how is my "
            "portfolio doing', overviews, totals, or MOIC across everything."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "resolve_company",
        "description": (
            "Look up a company by (partial) name and get its company_id. ALWAYS call this "
            "first when the question is about a specific company, before get_position / "
            "get_fees / get_valuation_history. If it returns more than one match (e.g. two "
            "'Northpeak' companies), ask the investor which one rather than guessing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Company name or fragment"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_position",
        "description": (
            "The investor's position in one company, aggregated across all rounds: current "
            "value, cost basis, the effective share price they paid per round, units and MOIC, "
            "plus any pending commitment. Use the company_id from resolve_company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"company_id": {"type": "string"}},
            "required": ["company_id"],
        },
    },
    {
        "name": "get_fees",
        "description": (
            "The fee schedule the investor pays on a company's deal(s): their effective "
            "management / performance (carry) / structuring / admin fees vs the deal standard, "
            "and which are discounted. Use the company_id from resolve_company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"company_id": {"type": "string"}},
            "required": ["company_id"],
        },
    },
    {
        "name": "get_valuation_history",
        "description": (
            "A company's valuation marks over time (per round) — share price and implied "
            "valuation moving up or down — and the investor's resulting MOIC. Use for 'how has "
            "X's valuation moved' or down-round questions. Use the company_id from resolve_company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"company_id": {"type": "string"}},
            "required": ["company_id"],
        },
    },
    {
        "name": "get_distributions",
        "description": (
            "Realised outcomes for the investor: exit proceeds and secondary sales, gross and "
            "net of the performance fee (carry), with what was actually received. Call this for "
            "'what have I received', exits, or realised returns."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_obligations",
        "description": (
            "The investor's upcoming capital calls and upcoming/overdue management & admin fees, "
            "with due dates, in their reporting currency. Call this for 'what do I owe', upcoming "
            "calls, or overdue fees."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_account_statement",
        "description": (
            "A plain account statement: totals of capital contributions, fees, and distributions "
            "(net of carry) in the reporting currency, and the net cashflow. Call this for "
            "'my statement' or a cash-in/cash-out summary."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

TOOL_NAMES = {t["name"] for t in TOOLS}


_HANDLERS = {
    "get_portfolio_overview": lambda s, i, **_: asdict(build_portfolio(s, i)),
    "resolve_company": lambda s, i, query, **_: resolve_company(s, i, query),
    "get_position": lambda s, i, company_id, **_: position_detail(s, i, company_id),
    "get_fees": lambda s, i, company_id, **_: fees_for_company(s, i, company_id),
    "get_valuation_history": lambda s, i, company_id, **_: valuation_history(s, i, company_id),
    "get_distributions": lambda s, i, **_: realised_outcomes(s, i),
    "get_obligations": lambda s, i, **_: upcoming_obligations(s, i),
    "get_account_statement": lambda s, i, **_: account_statement(s, i),
}


def dispatch(store: DataStore, investor_id: str, name: str, tool_input: dict | None) -> dict:
    """Run a tool against the engine, scoped to ``investor_id``. Never raises."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return {"error": f"unknown tool {name!r}"}
    try:
        return handler(store, investor_id, **(tool_input or {}))
    except TypeError as exc:  # missing/extra argument from the model
        return {"error": f"invalid arguments for {name!r}: {exc}"}
    except KeyError as exc:  # e.g. unknown company_id
        return {"error": f"not found: {exc}"}


def extract_citations(facts: object) -> list[dict]:
    """Recursively collect ``{source, row_id}`` citations from a facts payload."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if is_dataclass(node) and not isinstance(node, type):
            walk(asdict(node))
        elif isinstance(node, dict):
            if "source" in node and "row_id" in node:
                found.append({"source": node["source"], "row_id": node["row_id"]})
            else:
                for value in node.values():
                    walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)

    walk(facts)
    # De-duplicate, preserving order.
    seen: set[tuple] = set()
    unique: list[dict] = []
    for c in found:
        key = (c["source"], c["row_id"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique
