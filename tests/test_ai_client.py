# tests/test_ai_client.py
from unittest.mock import MagicMock, patch
from src.ai_layer.client import decide, AIDecision


def _make_message(content: str):
    """Build a mock anthropic Message-like object with TextBlock content."""
    block = MagicMock()
    block.text = content
    msg = MagicMock()
    msg.content = [block]
    return msg


def test_returns_ai_decision():
    """decide() always returns an AIDecision."""
    payload = '{"action": "BUY", "confidence": 0.82, "sl": 1918.0, "tp": 1945.0}'
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_message(payload)
        result = decide("test prompt")
    assert isinstance(result, AIDecision)


def test_buy_action_parsed():
    """Valid BUY JSON is parsed into an AIDecision with correct fields."""
    payload = '{"action": "BUY", "confidence": 0.82, "sl": 1918.0, "tp": 1945.0}'
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_message(payload)
        result = decide("test prompt")
    assert result.action == "BUY"
    assert result.confidence == 0.82
    assert result.sl == 1918.0
    assert result.tp == 1945.0
    assert result.error is None


def test_skip_action():
    """Valid SKIP JSON is parsed correctly."""
    payload = '{"action": "SKIP", "confidence": 0.3, "sl": 0.0, "tp": 0.0}'
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_message(payload)
        result = decide("test prompt")
    assert result.action == "SKIP"


def test_malformed_json_returns_skip_with_parse_error():
    """Malformed JSON → SKIP + AI_PARSE_ERROR (no exception raised to caller)."""
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = _make_message("not json at all")
        result = decide("test prompt")
    assert result.action == "SKIP"
    assert result.error == "AI_PARSE_ERROR"


def test_primary_model_fails_falls_back_to_secondary():
    """If Haiku raises, Sonnet is tried; total call_count == 2, result is successful."""
    payload = '{"action": "SELL", "confidence": 0.71, "sl": 1940.0, "tp": 1912.0}'
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        # First call raises, second call returns valid payload
        MockClient.return_value.messages.create.side_effect = [
            Exception("Haiku timeout"),
            _make_message(payload),
        ]
        result = decide("test prompt")
    assert result.action == "SELL"
    assert MockClient.return_value.messages.create.call_count == 2


def test_both_models_fail_returns_skip_api_error():
    """If both Haiku and Sonnet raise, decide() returns SKIP + AI_API_ERROR."""
    with patch("src.ai_layer.client.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.side_effect = Exception("API down")
        result = decide("test prompt")
    assert result.action == "SKIP"
    assert result.error == "AI_API_ERROR"
