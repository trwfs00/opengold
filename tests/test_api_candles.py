import pandas as pd
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Patch lifespan connect/disconnect so TestClient doesn't need MT5
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_candles_returns_list(client):
    sample = pd.DataFrame({
        "time": [pd.Timestamp("2026-03-25 10:00", tz="UTC")],
        "open": [1920.0], "high": [1921.0], "low": [1919.0],
        "close": [1920.5], "volume": [150.0],
    })
    with patch("src.api.routes.candles.fetch_candles", return_value=sample):
        resp = client.get("/api/candles?limit=1")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["close"] == 1920.5


def test_candles_mt5_disconnected(client):
    with patch("src.api.routes.candles.fetch_candles", return_value=pd.DataFrame()):
        with patch("src.api.routes.candles.is_connected", return_value=False):
            resp = client.get("/api/candles")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] == "MT5 disconnected"
    assert body["data"] is None


def test_account_returns_balance(client):
    with patch("src.api.routes.account.get_account_info", return_value={"balance": 10000.0, "equity": 10042.0, "currency": "USD"}):
        with patch("src.api.routes.account.get_positions", return_value=[]):
            resp = client.get("/api/account")
    assert resp.status_code == 200
    body = resp.json()
    assert body["balance"] == 10000.0
    assert body["positions"] == []


def test_account_mt5_disconnected(client):
    with patch("src.api.routes.account.get_account_info", return_value={}):
        with patch("src.api.routes.account.is_connected", return_value=False):
            resp = client.get("/api/account")
    assert resp.status_code == 200
    assert resp.json()["error"] == "MT5 disconnected"
