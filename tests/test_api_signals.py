import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_signals_empty_decisions_table(client):
    with patch("src.api.routes.signals.execute", return_value=[]):
        with patch("src.api.routes.signals.is_connected", return_value=True):
            resp = client.get("/api/signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["signals"] is None
    assert body["message"] == "No data yet"
    assert body["connected"] is True


def test_signals_returns_latest_row(client):
    import json
    signals_dict = {"ma_crossover": {"signal": "BUY", "confidence": 0.85}}
    row = ("TRENDING", 7.5, 1.2, json.dumps(signals_dict))
    with patch("src.api.routes.signals.execute", return_value=[row]):
        with patch("src.api.routes.signals.is_connected", return_value=True):
            resp = client.get("/api/signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["regime"] == "TRENDING"
    assert body["buy_score"] == 7.5
    assert body["signals"]["ma_crossover"]["signal"] == "BUY"


def test_decisions_returns_list(client):
    from datetime import datetime, timezone
    row = (datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc), "TRENDING", 7.5, 1.2, True, "BUY", 0.85, 1900.0, 1950.0, None, None)
    with patch("src.api.routes.decisions.execute", return_value=[row]):
        resp = client.get("/api/decisions?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["regime"] == "TRENDING"


def test_trades_returns_list(client):
    from datetime import datetime, timezone
    dt = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
    row = (dt, dt, "BUY", 0.01, 1920.0, 1940.0, 1910.0, 1950.0, 42.0, "WIN")
    with patch("src.api.routes.trades.execute", return_value=[row]):
        resp = client.get("/api/trades?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["result"] == "WIN"
    assert data[0]["pnl"] == 42.0
