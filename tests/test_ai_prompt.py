# tests/test_ai_prompt.py
from src.ai_layer.prompt import build_prompt


def _base_kwargs():
    return dict(
        journal="RECENT TRADES (last 1):\n[1] BUY TRENDING buy=7.1 sell=1.2 → WIN +$42",
        regime="TRENDING",
        buy_avg=7.1,
        sell_avg=1.2,
        buy_peak=8.0,
        sell_peak=2.0,
        window_minutes=5,
        price=1923.45,
        atr=12.55,
    )


def test_returns_string():
    """build_prompt always returns a str."""
    result = build_prompt(**_base_kwargs())
    assert isinstance(result, str)


def test_contains_regime():
    """Regime token appears in the prompt."""
    result = build_prompt(**_base_kwargs())
    assert "TRENDING" in result


def test_contains_price():
    """Current price appears in the prompt."""
    result = build_prompt(**_base_kwargs())
    assert "1923.45" in result or "1923" in result


def test_contains_atr():
    """ATR appears in the prompt."""
    result = build_prompt(**_base_kwargs())
    assert "12.55" in result or "12" in result


def test_journal_section_included_when_present():
    """Non-empty journal is embedded in the prompt."""
    result = build_prompt(**_base_kwargs())
    assert "RECENT TRADES" in result


def test_journal_section_omitted_when_empty():
    """When journal is empty string, no JOURNAL section appears."""
    kwargs = _base_kwargs()
    kwargs["journal"] = ""
    result = build_prompt(**kwargs)
    assert "JOURNAL" not in result


def test_task_section_present():
    """Task instruction (BUY/SELL/SKIP) is present in the prompt."""
    result = build_prompt(**_base_kwargs())
    # The prompt should mention all three possible actions
    assert "BUY" in result
    assert "SELL" in result
    assert "SKIP" in result
    # And request JSON output
    assert "JSON" in result or "json" in result


from src import config as _config


def test_gold_prompt_mentions_gold_role(monkeypatch):
    """Gold mode prompt describes a gold swing trader role."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100)
    monkeypatch.setattr(_config, "SYMBOL", "XAUUSD")
    result = build_prompt(
        journal="",
        regime="TRENDING_UP",
        buy_avg=7.0, sell_avg=2.0,
        buy_peak=8.0, sell_peak=3.0,
        window_minutes=5,
        price=1923.45,
        atr=12.55,
    )
    assert "gold" in result.lower()
    assert "XAUUSD" in result


def test_forex_prompt_mentions_forex_role(monkeypatch):
    """Forex mode prompt describes a forex scalper role."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "TP_PIPS_MIN", 4.0)
    monkeypatch.setattr(_config, "TP_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    result = build_prompt(
        journal="",
        regime="BREAKOUT",
        buy_avg=7.0, sell_avg=2.0,
        buy_peak=8.0, sell_peak=3.0,
        window_minutes=3,
        price=1.08500,
        atr=0.00120,
    )
    assert "forex" in result.lower() or "EURUSD" in result
    assert "pips" in result.lower()


def test_forex_prompt_uses_correct_price_format(monkeypatch):
    """Forex price should appear with 5 decimal places."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "EURUSD")
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "TP_PIPS_MIN", 4.0)
    monkeypatch.setattr(_config, "TP_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    result = build_prompt(
        journal="",
        regime="BREAKOUT",
        buy_avg=7.0, sell_avg=2.0,
        buy_peak=8.0, sell_peak=3.0,
        window_minutes=3,
        price=1.08500,
        atr=0.00120,
    )
    assert "1.08500" in result
