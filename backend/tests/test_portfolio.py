from datetime import datetime
from unittest.mock import patch

from app.models.ticker import Ticker
from app.models.position import Position
from app.services.risk_service import (
    compute_concentration,
    compute_drawdown_scenarios,
    generate_warnings,
    enrich_position,
)


# ── Unit tests for risk calculations ─────────────────────────────────────────

def test_enrich_position_with_price():
    class FakePosition:
        id = 1
        ticker_id = 1
        shares = 10
        avg_cost = 150.0

    result = enrich_position(FakePosition(), "AAPL", 200.0)
    assert result["cost_basis"] == 1500.0
    assert result["current_value"] == 2000.0
    assert result["unrealized_pnl"] == 500.0
    assert result["unrealized_pnl_pct"] == 33.33


def test_enrich_position_no_price():
    class FakePosition:
        id = 1
        ticker_id = 1
        shares = 10
        avg_cost = 150.0

    result = enrich_position(FakePosition(), "AAPL", None)
    assert result["current_value"] is None
    assert result["unrealized_pnl"] is None


def test_enrich_position_loss():
    class FakePosition:
        id = 1
        ticker_id = 1
        shares = 10
        avg_cost = 200.0

    result = enrich_position(FakePosition(), "AAPL", 150.0)
    assert result["unrealized_pnl"] == -500.0
    assert result["unrealized_pnl_pct"] == -25.0


def test_compute_concentration_single():
    positions = [{"symbol": "AAPL", "current_value": 10000.0}]
    result = compute_concentration(positions, 10000.0)
    assert result["largest_position_pct"] == 100.0
    assert result["top_3_concentration_pct"] == 100.0


def test_compute_concentration_multiple():
    positions = [
        {"symbol": "AAPL", "current_value": 5000.0},
        {"symbol": "MSFT", "current_value": 3000.0},
        {"symbol": "NVDA", "current_value": 2000.0},
    ]
    result = compute_concentration(positions, 10000.0)
    assert result["largest_position_pct"] == 50.0
    assert result["top_3_concentration_pct"] == 100.0


def test_compute_concentration_empty():
    result = compute_concentration([], 0)
    assert result["largest_position_pct"] is None


def test_drawdown_scenarios():
    result = compute_drawdown_scenarios(10000.0)
    assert result["drawdown_5pct"] == 500.0
    assert result["drawdown_10pct"] == 1000.0
    assert result["drawdown_20pct"] == 2000.0


def test_drawdown_scenarios_none():
    result = compute_drawdown_scenarios(None)
    assert result["drawdown_5pct"] == 0


def test_generate_warnings_high_concentration():
    positions = [{"symbol": "NVDA", "current_value": 8000.0, "unrealized_pnl_pct": 5.0}]
    warnings = generate_warnings(positions, 10000.0)
    assert any("NVDA" in w for w in warnings)
    assert any("concentrated" in w.lower() or "trimming" in w.lower() for w in warnings)


def test_generate_warnings_big_loss():
    positions = [{"symbol": "TSLA", "current_value": 5000.0, "unrealized_pnl_pct": -20.0}]
    warnings = generate_warnings(positions, 10000.0)
    assert any("TSLA" in w and "down" in w for w in warnings)


def test_generate_warnings_no_price():
    positions = [{"symbol": "AAPL", "current_value": None, "unrealized_pnl_pct": None}]
    warnings = generate_warnings(positions, 10000.0)
    assert any("AAPL" in w for w in warnings)


def test_generate_warnings_healthy():
    # All positions under 25% — no warnings expected
    positions = [
        {"symbol": "AAPL", "current_value": 2000.0, "unrealized_pnl_pct": 5.0},
        {"symbol": "MSFT", "current_value": 2000.0, "unrealized_pnl_pct": 2.0},
        {"symbol": "NVDA", "current_value": 2000.0, "unrealized_pnl_pct": 10.0},
        {"symbol": "TSLA", "current_value": 2000.0, "unrealized_pnl_pct": 3.0},
        {"symbol": "AMZN", "current_value": 2000.0, "unrealized_pnl_pct": 1.0},
    ]
    warnings = generate_warnings(positions, 10000.0)
    assert len(warnings) == 0


# ── API integration tests ─────────────────────────────────────────────────────

def test_risk_snapshot_no_positions(client):
    response = client.get("/api/portfolio/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["total_cost_basis"] == 0
    assert data["positions"] == []
    assert len(data["warnings"]) > 0


def test_list_positions_empty(client):
    response = client.get("/api/portfolio/positions")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_create_position_ticker_not_found(client):
    response = client.post("/api/portfolio/positions", json={
        "symbol": "FAKE",
        "shares": 10,
        "avg_cost": 100.0,
        "opened_at": "2024-01-01T00:00:00",
    })
    assert response.status_code == 404


def test_create_position_success(client, db):
    db.add(Ticker(symbol="AAPL", name="Apple"))
    db.commit()

    with patch("app.api.portfolio.get_current_price", return_value=200.0):
        response = client.post("/api/portfolio/positions", json={
            "symbol": "AAPL",
            "shares": 10,
            "avg_cost": 150.0,
            "opened_at": "2024-01-01T00:00:00",
        })

    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["cost_basis"] == 1500.0
    assert data["current_value"] == 2000.0
    assert data["unrealized_pnl"] == 500.0


def test_create_and_close_position(client, db):
    db.add(Ticker(symbol="MSFT", name="Microsoft"))
    db.commit()

    with patch("app.api.portfolio.get_current_price", return_value=400.0):
        create = client.post("/api/portfolio/positions", json={
            "symbol": "MSFT",
            "shares": 5,
            "avg_cost": 350.0,
            "opened_at": "2024-01-01T00:00:00",
        })
    assert create.status_code == 201
    position_id = create.json()["id"]

    close = client.delete(f"/api/portfolio/positions/{position_id}")
    assert close.status_code == 204

    positions = client.get("/api/portfolio/positions")
    assert positions.json()["total"] == 0


def test_portfolio_summary(client):
    response = client.get("/api/portfolio/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_positions" in data
    assert "total_cost_basis" in data
    assert "warnings_count" in data


def test_risk_snapshot_with_position(client, db):
    db.add(Ticker(symbol="NVDA", name="NVIDIA"))
    db.commit()

    with patch("app.api.portfolio.get_current_price", return_value=900.0):
        client.post("/api/portfolio/positions", json={
            "symbol": "NVDA",
            "shares": 10,
            "avg_cost": 500.0,
            "opened_at": "2024-01-01T00:00:00",
        })

    with patch("app.services.risk_service.get_current_prices", return_value={"NVDA": 900.0}):
        response = client.get("/api/portfolio/risk")

    assert response.status_code == 200
    data = response.json()
    assert data["total_cost_basis"] == 5000.0
    assert data["total_current_value"] == 9000.0
    assert data["total_unrealized_pnl"] == 4000.0
    assert data["largest_position_pct"] == 100.0