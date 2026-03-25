import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone


@pytest.fixture
def client():
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_stats_empty_trades(client):
    with patch("src.api.routes.stats.execute", return_value=[]):
        resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["win_rate"] is None
    assert body["total_pnl"] == 0.0
    assert body["pnl_curve"] == []


def test_stats_computes_correctly(client):
    dt1 = datetime(2026, 3, 25, 10, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 3, 25, 11, 0, tzinfo=timezone.utc)
    rows = [(dt1, 42.0, "WIN"), (dt2, -18.0, "LOSS")]
    with patch("src.api.routes.stats.execute", return_value=rows):
        resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["win_rate"] == 0.5
    assert body["total_pnl"] == 24.0
    assert body["avg_win"] == 42.0
    assert body["avg_loss"] == -18.0
    assert len(body["pnl_curve"]) == 2
    assert body["pnl_curve"][0]["time"] == int(dt1.timestamp())
    assert body["pnl_curve"][0]["value"] == 42.0
    assert body["pnl_curve"][1]["value"] == 24.0  # cumulative
