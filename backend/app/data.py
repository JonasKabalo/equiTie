"""Data layer.

Loads the 10 CSVs into pandas DataFrames once at startup (the whole dataset is
~5.3k rows). Provides typed lookups used by the deterministic compute engine.

Investor isolation is enforced *here*, in the data layer — every per-investor
accessor filters by ``investor_id``. The LLM is never what keeps investors apart.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import cast

import pandas as pd

from .config import DATA_DIR
from .fx import FXConverter

# Columns parsed as dates per file (only the ones we use).
_DATE_COLUMNS: dict[str, list[str]] = {
    "investors": ["onboarded_date"],
    "deals": ["deal_date"],
    "valuations": ["valuation_date"],
    "allocations": ["allocation_date"],
    "capital_calls": ["call_date", "due_date"],
    "fees": ["due_date"],
    "distributions": ["distribution_date"],
    "statement_lines": ["date"],
    "fx_rates": ["as_of"],
}


class DataStore:
    """In-memory view over the dataset with the lookups the engine needs."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

        def load(name: str) -> pd.DataFrame:
            return cast(
                "pd.DataFrame",
                pd.read_csv(data_dir / f"{name}.csv", parse_dates=_DATE_COLUMNS.get(name, [])),
            )

        self.investors = load("investors")
        self.companies = load("portfolio_companies")
        self.deals = load("deals")
        self.valuations = load("valuations")
        self.allocations = load("allocations")
        self.capital_calls = load("capital_calls")
        self.fees = load("fees")
        self.distributions = load("distributions")
        self.statement_lines = load("statement_lines")
        self.fx_rates_df = load("fx_rates")

        # FX rates: currency -> to_usd.
        rates = self.fx_rates_df.set_index("currency")["to_usd"]
        self.fx_rates: dict[str, float] = {str(c): float(v) for c, v in rates.items()}
        self.fx = FXConverter(self.fx_rates)

        # Latest valuation per deal (max valuation_date). Drives current value.
        latest_idx = self.valuations.groupby("deal_id")["valuation_date"].idxmax()
        self._latest_val = self.valuations.loc[latest_idx].set_index("deal_id")

        # Primary-key indexes for O(1) single-row access.
        self._deal_by_id = self.deals.set_index("deal_id")
        self._company_by_id = self.companies.set_index("company_id")
        self._investor_by_id = self.investors.set_index("investor_id")

    # -- single-row lookups ---------------------------------------------------
    def has_investor(self, investor_id: str) -> bool:
        return investor_id in self._investor_by_id.index

    def investor(self, investor_id: str) -> pd.Series:
        return self._investor_by_id.loc[investor_id]

    def deal(self, deal_id: str) -> pd.Series:
        return self._deal_by_id.loc[deal_id]

    def company(self, company_id: str) -> pd.Series:
        return self._company_by_id.loc[company_id]

    def latest_valuation(self, deal_id: str) -> pd.Series:
        return self._latest_val.loc[deal_id]

    def latest_share_price(self, deal_id: str) -> float:
        return float(self._latest_val.loc[deal_id, "share_price"])

    def latest_valuation_id(self, deal_id: str) -> str:
        return str(self._latest_val.loc[deal_id, "valuation_id"])

    # -- per-investor / per-allocation slices (investor-scoped) ---------------
    def allocations_for(self, investor_id: str) -> pd.DataFrame:
        mask = self.allocations["investor_id"] == investor_id
        return cast("pd.DataFrame", self.allocations[mask])

    def distributions_for_alloc(self, allocation_id: str) -> pd.DataFrame:
        mask = self.distributions["allocation_id"] == allocation_id
        return cast("pd.DataFrame", self.distributions[mask])

    def fees_for_investor(self, investor_id: str) -> pd.DataFrame:
        return cast("pd.DataFrame", self.fees[self.fees["investor_id"] == investor_id])

    def capital_calls_for_investor(self, investor_id: str) -> pd.DataFrame:
        mask = self.capital_calls["investor_id"] == investor_id
        return cast("pd.DataFrame", self.capital_calls[mask])

    def statement_for_investor(self, investor_id: str) -> pd.DataFrame:
        mask = self.statement_lines["investor_id"] == investor_id
        return cast("pd.DataFrame", self.statement_lines[mask])

    def allocation(self, investor_id: str, deal_id: str) -> pd.Series | None:
        rows = self.allocations[
            (self.allocations["investor_id"] == investor_id)
            & (self.allocations["deal_id"] == deal_id)
        ]
        if rows.empty:
            return None
        return rows.iloc[0]

    # -- disambiguation (similar names trap) ----------------------------------
    def find_companies(self, query: str) -> pd.DataFrame:
        q = query.strip().lower()
        mask = self.companies["company_name"].str.lower().str.contains(q, regex=False)
        return cast("pd.DataFrame", self.companies[mask])

    def deals_for_company(self, company_id: str) -> pd.DataFrame:
        return cast("pd.DataFrame", self.deals[self.deals["company_id"] == company_id])

    def valuations_for_deal(self, deal_id: str) -> pd.DataFrame:
        mask = self.valuations["deal_id"] == deal_id
        return cast("pd.DataFrame", self.valuations[mask]).sort_values("valuation_date")


@functools.lru_cache(maxsize=1)
def get_store() -> DataStore:
    """Process-wide singleton DataStore (loaded once)."""
    return DataStore(DATA_DIR)
