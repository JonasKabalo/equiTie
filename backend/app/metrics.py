"""Deterministic compute engine — the single source of truth for every number.

Formulas follow the dataset guide exactly:

* current value (per allocation) = units x latest share_price x live_fraction,
  FX-converted; **zero if the deal is Exited or Written Off**. ``live_fraction``
  is ``1 - sum(fraction_of_units)`` of that allocation's distributions, so a
  partial secondary leaves the unsold remainder marked live.
* MOIC = (current value + distributions net of carry) / capital contributed.
  ``net_amount`` from distributions.csv is used verbatim — carry is charged on
  the *gain*, not on gross proceeds, so it is never recomputed here.
* effective fees come from the allocation row; the discount is that row vs the
  deal's ``std_*`` schedule.
* DPI = net distributions / contributed; RVPI = current value / contributed.

The LLM never does any of this arithmetic; it only narrates these results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from .config import REPORT_DATE
from .data import DataStore

_EXIT_STATUSES = {"Exited", "Written Off"}
_OBLIGATION_FEE_TYPES = {"Management Fee", "Admin Fee"}


def _f(value: object) -> float:
    """Cast a (possibly numpy/NaN) value to a plain float, NaN -> 0.0."""
    f = float(value)  # type: ignore[arg-type]
    return 0.0 if f != f else f  # NaN check


def _iso(value: object) -> str | None:
    if value is None or (isinstance(value, float) and value != value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)


def _missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and value != value)


@dataclass(frozen=True)
class Citation:
    source: str
    row_id: str


@dataclass
class Position:
    """One investor's position in one deal (all amounts in deal currency)."""

    allocation_id: str
    investor_id: str
    deal_id: str
    company_id: str
    company_name: str
    sector: str
    round: str
    deal_currency: str
    commitment: float
    contributed: float
    outstanding_commitment: float
    effective_share_price: float
    entry_share_price: float
    units: float
    latest_share_price: float
    live_fraction: float
    current_value: float
    gross_distributions: float
    net_distributions: float
    moic: float | None
    allocation_status: str
    company_status: str
    is_pending: bool
    citations: list[Citation] = field(default_factory=list)


def build_positions(store: DataStore, investor_id: str) -> list[Position]:
    """All of an investor's positions, in deal currency. Investor-scoped."""
    positions: list[Position] = []
    for _, a in store.allocations_for(investor_id).iterrows():
        deal = store.deal(str(a["deal_id"]))
        company = store.company(str(deal["company_id"]))
        deal_status = str(deal["status"])
        is_pending = str(a["allocation_status"]) == "Pending"

        dists = store.distributions_for_alloc(str(a["allocation_id"]))
        sold = _f(dists["fraction_of_units"].sum()) if not dists.empty else 0.0
        live = max(0.0, 1.0 - sold)
        latest_price = store.latest_share_price(str(a["deal_id"]))

        if is_pending or deal_status in _EXIT_STATUSES:
            current_value = 0.0
        else:
            current_value = _f(a["units"]) * latest_price * live

        gross = _f(dists["gross_amount"].sum()) if not dists.empty else 0.0
        net = _f(dists["net_amount"].sum()) if not dists.empty else 0.0
        contributed = _f(a["contributed_amount"])
        moic = (current_value + net) / contributed if contributed > 0 else None

        citations = [Citation("allocations.csv", str(a["allocation_id"]))]
        citations.append(Citation("valuations.csv", store.latest_valuation_id(str(a["deal_id"]))))
        for dist_id in dists["distribution_id"]:
            citations.append(Citation("distributions.csv", str(dist_id)))

        positions.append(
            Position(
                allocation_id=str(a["allocation_id"]),
                investor_id=str(a["investor_id"]),
                deal_id=str(a["deal_id"]),
                company_id=str(deal["company_id"]),
                company_name=str(deal["company_name"]),
                sector=str(company["sector"]),
                round=str(deal["round"]),
                deal_currency=str(a["deal_currency"]),
                commitment=_f(a["commitment_amount"]),
                contributed=contributed,
                outstanding_commitment=_f(a["outstanding_commitment"]),
                effective_share_price=_f(a["effective_share_price"]),
                entry_share_price=_f(deal["entry_share_price"]),
                units=_f(a["units"]),
                latest_share_price=latest_price,
                live_fraction=live,
                current_value=current_value,
                gross_distributions=gross,
                net_distributions=net,
                moic=moic,
                allocation_status=str(a["allocation_status"]),
                company_status=str(company["status"]),
                is_pending=is_pending,
                citations=citations,
            )
        )
    return positions


@dataclass
class CompanyHolding:
    """A company-level holding, aggregated across rounds, in reporting currency."""

    company_id: str
    company_name: str
    sector: str
    company_status: str
    current_value: float
    contributed: float
    commitment: float
    net_distributions: float
    moic: float | None
    rounds: list[dict] = field(default_factory=list)


@dataclass
class Portfolio:
    investor_id: str
    investor_name: str
    reporting_currency: str
    has_holdings: bool
    total_committed: float
    total_contributed: float
    total_current_value: float
    total_net_distributions: float
    total_gross_distributions: float
    portfolio_moic: float | None
    dpi: float | None
    rvpi: float | None
    num_deals: int
    num_companies: int
    holdings: list[CompanyHolding] = field(default_factory=list)
    pending_commitments: list[dict] = field(default_factory=list)
    top_sectors: list[dict] = field(default_factory=list)
    signals: dict = field(default_factory=dict)


def build_portfolio(store: DataStore, investor_id: str) -> Portfolio:
    """Portfolio overview in the investor's reporting currency. Investor-scoped."""
    inv = store.investor(investor_id).to_dict()
    reporting = str(inv["reporting_currency"])
    positions = build_positions(store, investor_id)

    def to_rep(amount: float, ccy: str) -> float:
        return store.fx.convert(amount, ccy, reporting)

    funded = [p for p in positions if not p.is_pending]
    pending = [p for p in positions if p.is_pending]

    # Company-level aggregation (handles same company across multiple rounds).
    by_company: dict[str, CompanyHolding] = {}
    for p in funded:
        cv = to_rep(p.current_value, p.deal_currency)
        contributed = to_rep(p.contributed, p.deal_currency)
        commitment = to_rep(p.commitment, p.deal_currency)
        net = to_rep(p.net_distributions, p.deal_currency)
        holding = by_company.get(p.company_id)
        if holding is None:
            holding = CompanyHolding(
                company_id=p.company_id,
                company_name=p.company_name,
                sector=p.sector,
                company_status=p.company_status,
                current_value=0.0,
                contributed=0.0,
                commitment=0.0,
                net_distributions=0.0,
                moic=None,
            )
            by_company[p.company_id] = holding
        holding.current_value += cv
        holding.contributed += contributed
        holding.commitment += commitment
        holding.net_distributions += net
        holding.rounds.append(
            {
                "round": p.round,
                "deal_id": p.deal_id,
                "deal_currency": p.deal_currency,
                "effective_share_price": p.effective_share_price,
                "entry_share_price": p.entry_share_price,
                "latest_share_price": p.latest_share_price,
                "units": p.units,
                "current_value_reporting": cv,
                "contributed_reporting": contributed,
                "net_distributions_reporting": net,
                "moic": p.moic,
            }
        )
    for holding in by_company.values():
        if holding.contributed > 0:
            holding.moic = (holding.current_value + holding.net_distributions) / holding.contributed

    total_committed = sum(to_rep(p.commitment, p.deal_currency) for p in funded)
    total_contributed = sum(to_rep(p.contributed, p.deal_currency) for p in funded)
    total_cv = sum(to_rep(p.current_value, p.deal_currency) for p in funded)
    total_net = sum(to_rep(p.net_distributions, p.deal_currency) for p in funded)
    total_gross = sum(to_rep(p.gross_distributions, p.deal_currency) for p in funded)

    portfolio_moic = (total_cv + total_net) / total_contributed if total_contributed > 0 else None
    dpi = total_net / total_contributed if total_contributed > 0 else None
    rvpi = total_cv / total_contributed if total_contributed > 0 else None

    pending_commitments = [
        {
            "company_id": p.company_id,
            "company_name": p.company_name,
            "deal_id": p.deal_id,
            "round": p.round,
            "outstanding_commitment": p.outstanding_commitment,
            "deal_currency": p.deal_currency,
            "outstanding_reporting": to_rep(p.outstanding_commitment, p.deal_currency),
        }
        for p in pending
    ]

    # Top sectors by capital contributed (reporting currency).
    sector_totals: dict[str, dict] = {}
    for p in funded:
        s = sector_totals.setdefault(p.sector, {"sector": p.sector, "contributed": 0.0, "count": 0})
        s["contributed"] += to_rep(p.contributed, p.deal_currency)
        s["count"] += 1
    top_sectors = sorted(sector_totals.values(), key=lambda s: s["contributed"], reverse=True)

    num_deals = len({p.deal_id for p in positions})
    num_companies = len({p.company_id for p in positions})

    top_obj = max(by_company.values(), key=lambda h: h.current_value, default=None)
    concentration_pct = (
        round(top_obj.current_value / total_cv * 100, 1)
        if top_obj is not None and total_cv > 0
        else None
    )

    signals = {
        "tech_savviness": None if _missing(inv["tech_savviness"]) else str(inv["tech_savviness"]),
        "age": None if _missing(inv["age"]) else int(inv["age"]),
        "investor_type": str(inv["investor_type"]),
        "kyc_status": str(inv["kyc_status"]),
        "onboarded_date": _iso(inv["onboarded_date"]),
        "num_deals": num_deals,
        "num_companies": num_companies,
        "top_sectors": [s["sector"] for s in top_sectors[:3]],
        "top_holding": top_obj.company_name if top_obj is not None else None,
        "concentration_pct": concentration_pct,
    }

    return Portfolio(
        investor_id=investor_id,
        investor_name=str(inv["investor_name"]),
        reporting_currency=reporting,
        has_holdings=len(by_company) > 0,
        total_committed=total_committed,
        total_contributed=total_contributed,
        total_current_value=total_cv,
        total_net_distributions=total_net,
        total_gross_distributions=total_gross,
        portfolio_moic=portfolio_moic,
        dpi=dpi,
        rvpi=rvpi,
        num_deals=num_deals,
        num_companies=num_companies,
        holdings=sorted(by_company.values(), key=lambda h: h.current_value, reverse=True),
        pending_commitments=pending_commitments,
        top_sectors=top_sectors,
        signals=signals,
    )


def company_position(store: DataStore, investor_id: str, company_id: str) -> CompanyHolding | None:
    """An investor's aggregated position in one company (across all its rounds)."""
    portfolio = build_portfolio(store, investor_id)
    for holding in portfolio.holdings:
        if holding.company_id == company_id:
            return holding
    return None


def fees_on_deal(store: DataStore, investor_id: str, deal_id: str) -> dict | None:
    """The fee schedule an investor pays on a deal: effective rates vs deal standard."""
    a = store.allocation(investor_id, deal_id)
    if a is None:
        return None
    deal = store.deal(deal_id)
    # (label, allocation column, deal-standard column, unit)
    spec = [
        ("Management fee", "mgmt_fee_pct", "std_mgmt_fee_pct", "%"),
        ("Performance fee (carry)", "performance_fee_pct", "std_performance_fee_pct", "%"),
        ("Structuring fee", "structuring_fee_pct", "std_structuring_fee_pct", "%"),
        ("Admin fee", "admin_fee_usd", "std_admin_fee_usd", "USD"),
    ]
    items = []
    for label, alloc_col, std_col, unit in spec:
        eff = _f(a[alloc_col])
        std = _f(deal[std_col])
        items.append(
            {
                "fee": label,
                "effective": eff,
                "standard": std,
                "unit": unit,
                "discounted": eff < std,
            }
        )
    return {
        "investor_id": investor_id,
        "deal_id": deal_id,
        "company_name": str(deal["company_name"]),
        "round": str(deal["round"]),
        "fee_discount_flag": str(a["fee_discount"]),
        "has_discount": any(i["discounted"] for i in items),
        "items": items,
        "citations": [
            {"source": "allocations.csv", "row_id": str(a["allocation_id"])},
            {"source": "deals.csv", "row_id": deal_id},
        ],
    }


def upcoming_obligations(store: DataStore, investor_id: str) -> dict:
    """Upcoming capital calls + upcoming/overdue management & admin fees."""
    reporting = str(store.investor(investor_id)["reporting_currency"])

    def to_rep(amount: float, ccy: str) -> float:
        return store.fx.convert(amount, ccy, reporting)

    items: list[dict] = []

    calls = store.capital_calls_for_investor(investor_id)
    for _, c in calls[calls["status"] == "Upcoming"].iterrows():
        items.append(
            {
                "kind": "Capital call",
                "deal_id": str(c["deal_id"]),
                "amount": _f(c["amount"]),
                "currency": str(c["currency"]),
                "amount_reporting": to_rep(_f(c["amount"]), str(c["currency"])),
                "due_date": _iso(c["due_date"]),
                "status": str(c["status"]),
                "citation": {"source": "capital_calls.csv", "row_id": str(c["call_id"])},
            }
        )

    fees = store.fees_for_investor(investor_id)
    fee_mask = fees["status"].isin(["Upcoming", "Overdue"]) & fees["fee_type"].isin(
        list(_OBLIGATION_FEE_TYPES)
    )
    for _, f in fees[fee_mask].iterrows():
        items.append(
            {
                "kind": str(f["fee_type"]),
                "deal_id": str(f["deal_id"]),
                "amount": _f(f["amount"]),
                "currency": str(f["currency"]),
                "amount_reporting": to_rep(_f(f["amount"]), str(f["currency"])),
                "due_date": _iso(f["due_date"]),
                "status": str(f["status"]),
                "citation": {"source": "fees.csv", "row_id": str(f["fee_id"])},
            }
        )

    upcoming = [i for i in items if i["status"] == "Upcoming"]
    overdue = [i for i in items if i["status"] == "Overdue"]
    return {
        "investor_id": investor_id,
        "reporting_currency": reporting,
        "upcoming": sorted(upcoming, key=lambda i: i["due_date"] or ""),
        "overdue": sorted(overdue, key=lambda i: i["due_date"] or ""),
        "total_upcoming_reporting": sum(i["amount_reporting"] for i in upcoming),
        "total_overdue_reporting": sum(i["amount_reporting"] for i in overdue),
        "report_date": REPORT_DATE.isoformat(),
    }


def account_statement(store: DataStore, investor_id: str) -> dict:
    """Plain account statement: capital contributions, fees and distributions.

    Lines are signed and in their own currency (negative = cash out, positive =
    cash in, net of carry). Each is FX-converted to the reporting currency.
    """
    reporting = str(store.investor(investor_id)["reporting_currency"])
    lines = store.statement_for_investor(investor_id)

    by_type: dict[str, float] = {}
    for _, line in lines.iterrows():
        amount_rep = store.fx.convert(_f(line["amount"]), str(line["currency"]), reporting)
        by_type[str(line["type"])] = by_type.get(str(line["type"]), 0.0) + amount_rep

    net = sum(by_type.values())
    return {
        "investor_id": investor_id,
        "reporting_currency": reporting,
        "by_type": [{"type": t, "amount_reporting": v} for t, v in sorted(by_type.items())],
        "net_cashflow_reporting": net,
        "line_count": int(len(lines)),
    }


def realised_outcomes(store: DataStore, investor_id: str) -> dict:
    """Distributions and exits realised by the investor, gross and net of carry."""
    reporting = str(store.investor(investor_id)["reporting_currency"])
    alloc_ids = set(store.allocations_for(investor_id)["allocation_id"])
    dists = store.distributions[store.distributions["allocation_id"].isin(list(alloc_ids))]
    items = []
    for _, d in dists.iterrows():
        deal = store.deal(str(d["deal_id"]))
        net = _f(d["net_amount"])
        items.append(
            {
                "company_name": str(deal["company_name"]),
                "round": str(deal["round"]),
                "type": str(d["distribution_type"]),
                "date": _iso(d["distribution_date"]),
                "gross": _f(d["gross_amount"]),
                "performance_fee": _f(d["performance_fee_amount"]),
                "net": net,
                "currency": str(d["currency"]),
                "fraction_of_units": _f(d["fraction_of_units"]),
                "net_reporting": store.fx.convert(net, str(d["currency"]), reporting),
                "citation": {"source": "distributions.csv", "row_id": str(d["distribution_id"])},
            }
        )
    return {
        "investor_id": investor_id,
        "reporting_currency": reporting,
        "distributions": items,
        "total_net_reporting": sum(i["net_reporting"] for i in items),
        "count": len(items),
    }


def resolve_company(store: DataStore, investor_id: str, query: str) -> dict:
    """Disambiguate a company name (handles similar names like the two Northpeaks)."""
    matches = store.find_companies(query)
    allocs = store.allocations_for(investor_id)
    held_ids = {str(store.deal(str(a["deal_id"]))["company_id"]) for _, a in allocs.iterrows()}
    out = [
        {
            "company_id": str(r["company_id"]),
            "company_name": str(r["company_name"]),
            "sector": str(r["sector"]),
            "company_status": str(r["status"]),
            "you_hold": str(r["company_id"]) in held_ids,
        }
        for _, r in matches.iterrows()
    ]
    return {"query": query, "matches": out, "count": len(out)}


def position_detail(store: DataStore, investor_id: str, company_id: str) -> dict:
    """An investor's position in one company: funded holding (across rounds) + any pending."""
    company = store.company(company_id)
    portfolio = build_portfolio(store, investor_id)
    holding = next((h for h in portfolio.holdings if h.company_id == company_id), None)
    pending = [pc for pc in portfolio.pending_commitments if pc["company_id"] == company_id]
    return {
        "company_id": company_id,
        "company_name": str(company["company_name"]),
        "sector": str(company["sector"]),
        "company_status": str(company["status"]),
        "you_hold": holding is not None,
        "holding": asdict(holding) if holding is not None else None,
        "pending": pending,
        "reporting_currency": portfolio.reporting_currency,
    }


def fees_for_company(store: DataStore, investor_id: str, company_id: str) -> dict:
    """Fee schedule (effective vs standard) for each round the investor holds of a company."""
    company = store.company(company_id)
    deals = store.deals_for_company(company_id)
    out = []
    for _, deal in deals.iterrows():
        fees = fees_on_deal(store, investor_id, str(deal["deal_id"]))
        if fees is not None:
            out.append(fees)
    return {
        "company_id": company_id,
        "company_name": str(company["company_name"]),
        "deals": out,
        "held_count": len(out),
    }


def valuation_history(store: DataStore, investor_id: str, company_id: str) -> dict:
    """A company's valuation marks over time (per round) and the investor's resulting MOIC."""
    company = store.company(company_id)
    deals = store.deals_for_company(company_id)
    rounds = []
    for _, deal in deals.iterrows():
        deal_id = str(deal["deal_id"])
        marks_df = store.valuations_for_deal(deal_id)
        marks = [
            {
                "date": _iso(v["valuation_date"]),
                "share_price": _f(v["share_price"]),
                "company_valuation_m": _f(v["company_valuation_m"]),
                "mark_source": str(v["mark_source"]),
                "multiple_vs_entry": _f(v["multiple_vs_entry"]),
                "citation": {"source": "valuations.csv", "row_id": str(v["valuation_id"])},
            }
            for _, v in marks_df.iterrows()
        ]
        rounds.append(
            {
                "deal_id": deal_id,
                "round": str(deal["round"]),
                "deal_currency": str(deal["deal_currency"]),
                "entry_share_price": _f(deal["entry_share_price"]),
                "marks": marks,
            }
        )
    holding = next(
        (h for h in build_portfolio(store, investor_id).holdings if h.company_id == company_id),
        None,
    )
    return {
        "company_id": company_id,
        "company_name": str(company["company_name"]),
        "sector": str(company["sector"]),
        "company_status": str(company["status"]),
        "you_hold": holding is not None,
        "your_moic": holding.moic if holding is not None else None,
        "rounds": rounds,
    }
