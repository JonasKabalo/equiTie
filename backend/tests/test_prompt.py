"""System prompt — profile injection, guardrails, and personalisation."""

from __future__ import annotations

from app.data import DataStore
from app.prompt import build_system_prompt


def test_prompt_has_profile_and_guardrails(store: DataStore) -> None:
    p = build_system_prompt(store, "INV001")
    assert "INV001" in p
    assert "GBP" in p  # reporting currency
    assert "investment advice" in p.lower()
    assert "resolve_company" in p
    assert "only this investor" in p.lower()
    assert "MOIC" in p


def test_prompt_personalises_for_high_tech(store: DataStore) -> None:
    # INV001 is High tech-savviness.
    p = build_system_prompt(store, "INV001").lower()
    assert "sophisticated" in p or "data-dense" in p


def test_prompt_personalises_for_low_tech(store: DataStore) -> None:
    low = store.investors[store.investors["tech_savviness"] == "Low"]
    if low.empty:
        return  # no Low-tech investor in the dataset
    investor_id = str(low.iloc[0]["investor_id"])
    p = build_system_prompt(store, investor_id).lower()
    assert "plain language" in p
