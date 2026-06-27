"""Tool dispatch — grounding, citations, and investor scoping."""

from __future__ import annotations

from app.data import DataStore
from app.tools import TOOL_NAMES, dispatch, extract_citations


def test_portfolio_tool_is_investor_scoped(store: DataStore) -> None:
    assert dispatch(store, "INV001", "get_portfolio_overview", {})["has_holdings"] is True
    assert dispatch(store, "INV022", "get_portfolio_overview", {})["has_holdings"] is False


def test_resolve_company_disambiguates(store: DataStore) -> None:
    facts = dispatch(store, "INV001", "resolve_company", {"query": "Northpeak"})
    assert facts["count"] == 2


def test_get_position_aggregates_rounds(store: DataStore) -> None:
    resolved = dispatch(store, "INV001", "resolve_company", {"query": "Forgecraft"})
    company_id = resolved["matches"][0]["company_id"]
    facts = dispatch(store, "INV001", "get_position", {"company_id": company_id})
    assert facts["you_hold"] is True
    assert len(facts["holding"]["rounds"]) >= 2


def test_get_fees_carries_citations(store: DataStore) -> None:
    resolved = dispatch(store, "INV041", "resolve_company", {"query": "Forgecraft"})
    company_id = resolved["matches"][0]["company_id"]
    facts = dispatch(store, "INV041", "get_fees", {"company_id": company_id})
    cites = extract_citations(facts)
    assert any(c["source"] == "allocations.csv" for c in cites)
    assert any(c["source"] == "deals.csv" for c in cites)


def test_distributions_tool(store: DataStore) -> None:
    facts = dispatch(store, "INV011", "get_distributions", {})  # Helianthe exit
    assert facts["count"] >= 1
    assert facts["total_net_reporting"] > 0


def test_dispatch_never_raises(store: DataStore) -> None:
    assert "error" in dispatch(store, "INV001", "no_such_tool", {})
    assert "error" in dispatch(store, "INV001", "get_position", {})  # missing company_id


def test_tool_names_complete() -> None:
    assert "get_portfolio_overview" in TOOL_NAMES
    assert "resolve_company" in TOOL_NAMES
