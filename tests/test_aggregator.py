from src.aggregator.scorer import aggregate, AggregateResult
from src.strategies.base import SignalResult


def _sig(name, signal, confidence=0.8):
    return SignalResult(name=name, signal=signal, confidence=confidence)


def test_returns_aggregate_result():
    signals = [_sig("ma_crossover", "BUY")]
    result = aggregate(signals, "TRENDING")
    assert isinstance(result, AggregateResult)
    assert hasattr(result, "buy_score")
    assert hasattr(result, "sell_score")
    assert hasattr(result, "regime")
    assert hasattr(result, "signals")


def test_all_buy_gives_high_buy_score():
    signals = [
        _sig("ma_crossover", "BUY"),
        _sig("macd", "BUY"),
    ]
    result = aggregate(signals, "TRENDING")
    assert result.buy_score > result.sell_score
    assert result.buy_score > 0


def test_neutral_contributes_zero():
    signals = [_sig("ma_crossover", "NEUTRAL", 0.9)]
    result = aggregate(signals, "TRENDING")
    assert result.buy_score == 0.0
    assert result.sell_score == 0.0


def test_sell_signals_accumulate():
    signals = [_sig("rsi", "SELL", 1.0), _sig("bollinger", "SELL", 1.0)]
    result = aggregate(signals, "RANGING")
    assert result.sell_score > result.buy_score


def test_regime_weights_applied():
    # In TRENDING, ma_crossover weight=1.5; in RANGING, weight=0.5
    signals = [_sig("ma_crossover", "BUY", 1.0)]
    trending = aggregate(signals, "TRENDING")
    ranging = aggregate(signals, "RANGING")
    assert trending.buy_score > ranging.buy_score


def test_unknown_strategy_uses_weight_1():
    signals = [_sig("unknown_strategy", "BUY", 1.0)]
    result = aggregate(signals, "TRENDING")
    assert result.buy_score == 1.0
