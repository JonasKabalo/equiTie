"""API smoke tests (FastAPI TestClient)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["report_date"] == "2026-06-25"
    assert body["counts"]["investors"] == 112


def test_investors_list() -> None:
    r = client.get("/api/investors")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 112
    assert all("investor_id" in d and "tech_savviness" in d for d in data)


def test_portfolio_ok() -> None:
    r = client.get("/api/portfolio/INV001")
    assert r.status_code == 200
    assert r.json()["has_holdings"] is True


def test_portfolio_unknown_investor() -> None:
    r = client.get("/api/portfolio/INV999")
    assert r.status_code == 404
