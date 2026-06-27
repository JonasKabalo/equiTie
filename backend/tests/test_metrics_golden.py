"""Golden tests — every number here is hand-verified against the raw CSV rows.

These pin the core metrics so a regression in the engine fails loudly.
"""

from __future__ import annotations

import pytest

from app.data import DataStore
from app.metrics import Position, build_positions


def _positions(store: DataStore, investor_id: str) -> dict[str, Position]:
    return {p.allocation_id: p for p in build_positions(store, investor_id)}


def test_forgecraft_seed_value_and_moic(store: DataStore) -> None:
    # ALC0001: 40,000 USD / 2.25 effective price = 17,777.78 units; latest mark 15.4.
    p = _positions(store, "INV001")["ALC0001"]
    assert p.units == pytest.approx(17777.78, abs=0.01)
    assert p.latest_share_price == pytest.approx(15.4)
    assert p.current_value == pytest.approx(17777.78 * 15.4, abs=0.01)  # 273,777.81 USD
    assert p.net_distributions == 0.0
    assert p.moic == pytest.approx((17777.78 * 15.4) / 40000, rel=1e-9)  # 6.844
    # Into the investor's reporting currency (GBP): / 1.35.
    gbp = store.fx.convert(p.current_value, "USD", "GBP")
    assert gbp == pytest.approx(17777.78 * 15.4 / 1.35, abs=0.01)  # 202,798.38 GBP


def test_helianthe_exit_net_of_carry(store: DataStore) -> None:
    # ALC0223: full exit. Carry is on the GAIN: 25% x (139,500 - 93,000) = 11,625.
    p = _positions(store, "INV011")["ALC0223"]
    assert p.company_status == "Exited"
    assert p.current_value == 0.0
    assert p.gross_distributions == pytest.approx(139500.0)
    assert p.net_distributions == pytest.approx(127875.0)
    assert p.moic == pytest.approx(127875.0 / 93000.0, rel=1e-9)  # 1.375 net (1.5x gross)


def test_tallybook_partial_secondary_coexists(store: DataStore) -> None:
    # ALC0520: sold 30% in a secondary; remaining 70% still marked live at 12.0.
    p = _positions(store, "INV013")["ALC0520"]
    assert p.live_fraction == pytest.approx(0.7)
    assert p.current_value == pytest.approx(4200 * 12.0 * 0.7)  # 35,280
    assert p.net_distributions == pytest.approx(13356.0)
    assert p.moic == pytest.approx((35280 + 13356) / 21000)  # 2.316


def test_yappio_write_off_is_total_loss(store: DataStore) -> None:
    # ALC0237: Yappio written off, latest mark 0 -> value 0, MOIC 0.
    p = _positions(store, "INV010")["ALC0237"]
    assert p.company_status == "Written Off"
    assert p.latest_share_price == 0.0
    assert p.current_value == 0.0
    assert p.moic == 0.0


def test_pending_allocation_not_deployed(store: DataStore) -> None:
    # ALC0542: signed but unfunded (0% contributed) -> excluded value, MOIC undefined.
    p = _positions(store, "INV021")["ALC0542"]
    assert p.is_pending is True
    assert p.current_value == 0.0
    assert p.moic is None
    assert p.outstanding_commitment == pytest.approx(75000.0)
