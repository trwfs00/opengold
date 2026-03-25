# tests/test_ai_prompt.py
from src.ai_layer.prompt import build_prompt


def _base_kwargs():
    return dict(
        journal="RECENT TRADES (last 1):\n[1] BUY TRENDING buy=7.1 sell=1.2 → WIN +$42",
        regime="TRENDING",
        buy_score=7.1,
        sell_score=1.2,
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
