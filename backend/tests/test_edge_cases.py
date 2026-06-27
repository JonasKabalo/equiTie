"""Edge-case behaviours from the dataset guide's "traps" list."""

from __future__ import annotations

import pytest

from app.data import DataStore
from app.metrics import (
    account_statement,
    build_portfolio,
    company_position,
    fees_on_deal,
    upcoming_obligations,
)


def test_zero_holdings_investor(store: DataStore) -> None:
    pf = build_portfolio(store, "INV022")  # Henrik Sorensen — onboarded, holds nothing
    assert pf.has_holdings is False
    assert pf.total_current_value == 0.0
    assert pf.portfolio_moic is None
    assert pf.holdings == []


def test_second_zero_holdings_investor(store: DataStore) -> None:
    pf = build_portfolio(store, "INV023")  # Lara Greco
    assert pf.has_holdings is False


def test_pending_only_portfolio(store: DataStore) -> None:
    pf = build_portfolio(store, "INV021")  # Grace Okafor — single pending Helixar allocation
    assert pf.has_holdings is False
    assert pf.portfolio_moic is None
    assert len(pf.pending_commitments) == 1
    pc = pf.pending_commitments[0]
    assert pc["company_name"] == "Helixar Bio"
    assert pc["outstanding_reporting"] == pytest.approx(75000.0)  # reports in USD


def test_multi_round_company_aggregation(store: DataStore) -> None:
    holding = company_position(store, "INV001", "CO001")  # Forgecraft across rounds
    assert holding is not None
    assert len(holding.rounds) >= 2
    assert holding.current_value > 0
    assert holding.moic is not None


def test_similar_company_names_disambiguation(store: DataStore) -> None:
    matches = store.find_companies("Northpeak")
    assert len(matches) == 2
    assert set(matches["sector"]) == {"Data / Analytics", "Digital Health"}


def test_fee_discount_vs_standard(store: DataStore) -> None:
    fees = fees_on_deal(store, "INV041", "DEAL001")  # ALC0006: mgmt 0, perf 15, struct 4, admin 0
    assert fees is not None
    assert fees["has_discount"] is True
    items = {i["fee"]: i for i in fees["items"]}
    assert items["Management fee"]["discounted"] is True  # 0% vs 2% standard
    assert items["Admin fee"]["discounted"] is True  # 0 vs 450 USD standard
    assert items["Structuring fee"]["discounted"] is False  # 4% == 4% standard


def test_upcoming_obligations_include_fees(store: DataStore) -> None:
    obs = upcoming_obligations(store, "INV001")
    assert obs["reporting_currency"] == "GBP"
    kinds = {i["kind"] for i in obs["upcoming"]}
    assert "Management Fee" in kinds
    assert obs["total_upcoming_reporting"] > 0


def test_account_statement(store: DataStore) -> None:
    st = account_statement(store, "INV001")
    assert st["reporting_currency"] == "GBP"
    assert st["line_count"] > 0
    types = {row["type"] for row in st["by_type"]}
    assert "Capital Contribution" in types
