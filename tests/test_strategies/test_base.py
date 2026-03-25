import pytest
from src.strategies.base import SignalResult


def test_signal_result_fields():
    sr = SignalResult(name="TestStrategy", signal="BUY", confidence=0.8)
    assert sr.name == "TestStrategy"
    assert sr.signal == "BUY"
    assert sr.confidence == 0.8


def test_signal_result_sell():
    sr = SignalResult(name="S", signal="SELL", confidence=0.5)
    assert sr.signal == "SELL"


def test_signal_result_neutral():
    sr = SignalResult(name="S", signal="NEUTRAL", confidence=0.0)
    assert sr.signal == "NEUTRAL"


def test_signal_result_invalid_signal():
    with pytest.raises(ValueError):
        SignalResult(name="S", signal="LONG", confidence=0.5)


def test_confidence_clipped_above():
    sr = SignalResult(name="S", signal="BUY", confidence=1.5)
    assert sr.confidence == 1.0


def test_confidence_clipped_below():
    sr = SignalResult(name="S", signal="BUY", confidence=-0.3)
    assert sr.confidence == 0.0
