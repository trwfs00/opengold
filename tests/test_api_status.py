import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta


@pytest.fixture
def client():
    with patch("src.api.app.connect"), patch("src.api.app.disconnect"):
        from src.api.app import app
        with TestClient(app) as c:
            yield c


def test_status_bot_alive(client):
    recent = datetime.now(timezone.utc) - timedelta(seconds=10)
    with patch("src.api.routes.status.execute", return_value=[(recent,)]):
        with patch("src.api.routes.status.get_kill_switch_state", return_value=False):
            resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bot_alive"] is True
    assert body["kill_switch_active"] is False


def test_status_bot_offline(client):
    stale = datetime.now(timezone.utc) - timedelta(hours=1)
    with patch("src.api.routes.status.execute", return_value=[(stale,)]):
        with patch("src.api.routes.status.get_kill_switch_state", return_value=False):
            resp = client.get("/api/status")
    body = resp.json()
    assert body["bot_alive"] is False


def test_killswitch_post(client):
    with patch("src.api.routes.killswitch.set_kill_switch") as mock_ks:
        resp = client.post("/api/killswitch", json={"active": True})
    assert resp.status_code == 200
    mock_ks.assert_called_once_with(True)
    assert resp.json()["active"] is True
