from src.risk.engine import validate, RiskResult


def test_valid_buy_passes():
    result = validate(
        action="BUY", confidence=0.8, sl=1917.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=1, kill_switch=False,
    )
    assert result.approved
    assert result.lot_size > 0


def test_returns_risk_result():
    result = validate(
        action="BUY", confidence=0.8, sl=1917.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert isinstance(result, RiskResult)


def test_kill_switch_blocks():
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=True,
    )
    assert not result.approved
    assert result.block_reason == "KILL_SWITCH_ACTIVE"


def test_low_confidence_blocked():
    result = validate(
        action="BUY", confidence=0.5, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=1, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "LOW_CONFIDENCE"


def test_sl_too_tight_blocked():
    # SL distance only $0.50 — below MIN_SL_USD=3.0
    result = validate(
        action="BUY", confidence=0.9, sl=1919.5, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_sl_too_wide_blocked():
    # SL distance = $60 — above MAX_SL_USD=50.0
    result = validate(
        action="BUY", confidence=0.9, sl=1860.0, tp=1980.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_below_min_lot_blocked():
    # Tiny balance → computed lot below 0.01
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=100.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "BELOW_MIN_LOT"


def test_max_trades_blocks():
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=3, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "MAX_TRADES_REACHED"


def test_lot_sizing_correct():
    # balance=10000, risk=1%=$100, SL=10 USD → lot = 100/(10*100) = 0.10
    result = validate(
        action="BUY", confidence=0.8, sl=1910.0, tp=1950.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.approved
    assert abs(result.lot_size - 0.10) < 0.01
