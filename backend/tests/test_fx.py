"""FX conversion — all cross-currency goes via USD.

Rates as of the report date: USD 1.0, GBP 1.35, EUR 1.09, AED 0.2723 (to_usd).
"""

from __future__ import annotations

import pytest

from app.data import DataStore


def test_identity(store: DataStore) -> None:
    assert store.fx.convert(1000.0, "USD", "USD") == 1000.0


def test_gbp_to_usd(store: DataStore) -> None:
    # 1 GBP = 1.35 USD.
    assert store.fx.convert(1000.0, "GBP", "USD") == pytest.approx(1350.0)


def test_eur_to_gbp_via_usd(store: DataStore) -> None:
    # 1000 EUR = 1090 USD = 1090 / 1.35 GBP.
    assert store.fx.convert(1000.0, "EUR", "GBP") == pytest.approx(1090.0 / 1.35)


def test_aed_to_gbp_via_usd(store: DataStore) -> None:
    # Admin fees are billed in USD even on AED deals — but plain AED still converts via USD.
    assert store.fx.convert(1000.0, "AED", "GBP") == pytest.approx(1000.0 * 0.2723 / 1.35)


def test_unknown_currency_raises(store: DataStore) -> None:
    with pytest.raises(KeyError):
        store.fx.convert(100.0, "JPY", "USD")
