from src.risk.engine import validate, RiskResult
from src import config as _config


def test_valid_buy_passes(monkeypatch):
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 3)
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
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


def test_kill_switch_blocks(monkeypatch):
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 3)
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=True,
    )
    assert not result.approved
    assert result.block_reason == "KILL_SWITCH_ACTIVE"


def test_low_confidence_blocked(monkeypatch):
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 3)
    result = validate(
        action="BUY", confidence=0.5, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=1, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "LOW_CONFIDENCE"


def test_sl_too_tight_blocked(monkeypatch):
    # SL distance only $0.50 — below MIN_SL_USD=3.0
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    result = validate(
        action="BUY", confidence=0.9, sl=1919.5, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_sl_too_wide_blocked(monkeypatch):
    # SL distance = $60 — above MAX_SL_USD=50.0
    monkeypatch.setattr(_config, "MAX_SL_USD", 50.0)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    result = validate(
        action="BUY", confidence=0.9, sl=1860.0, tp=1980.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_below_min_lot_blocked(monkeypatch):
    # Tiny balance → computed lot below 0.01
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=100.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "BELOW_MIN_LOT"


def test_max_trades_blocks(monkeypatch):
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 3)
    result = validate(
        action="BUY", confidence=0.9, sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0, open_trades=3, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "MAX_TRADES_REACHED"


def test_lot_sizing_correct(monkeypatch):
    # balance=10000, risk=1%=$100, SL=10 USD → lot = 100/(10*100) = 0.10
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    result = validate(
        action="BUY", confidence=0.8, sl=1910.0, tp=1950.0,
        entry=1920.0, balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.approved
    assert abs(result.lot_size - 0.10) < 0.01


# ── Forex (GBPUSD) tests ──────────────────────────────────────────────────────

def test_forex_valid_buy_passes(monkeypatch):
    """GBPUSD buy with 4-pip SL and 6-pip TP (ratio 1.5x) should be approved."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "GBPUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # entry=1.08500, sl=1.08460 (4 pips), tp=1.08560 (6 pips) → ratio=1.5x ✓
    result = validate(
        action="BUY", confidence=0.8,
        sl=1.08460, tp=1.08560,
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.approved
    assert result.lot_size > 0


def test_forex_lot_size_correct(monkeypatch):
    """Forex lot = risk_amount / (sl_pips * pip_value_per_lot)."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "GBPUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # risk=$100 (1% of $10000), SL=4 pips, PipValue=$10 → lot=100/(4*10)=2.50
    # tp=1.08560 (6 pips) → ratio=1.5x ≥ 1.3 ✓
    result = validate(
        action="BUY", confidence=0.8,
        sl=1.08460, tp=1.08560,
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.lot_size == 2.50


def test_forex_sl_too_tight_blocked(monkeypatch):
    """SL < SL_PIPS_MIN should return INVALID_SL for Forex."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "GBPUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # SL = 2 pips (below SL_PIPS_MIN=3)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08480, tp=1.08550,   # 2 pips SL, 7 pips TP
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_forex_sl_too_wide_blocked(monkeypatch):
    """SL > SL_PIPS_MAX should return INVALID_SL for Forex."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "GBPUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # SL = 8 pips (above SL_PIPS_MAX=5)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08420, tp=1.08600,   # 8 pips SL
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_SL"


def test_forex_tp_fails_rr_ratio(monkeypatch):
    """TP that doesn't satisfy MIN_RR_RATIO should return INVALID_TP for Forex."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "GBPUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # SL=4 pips, TP=3 pips → tp_pips(3) < SL_PIPS_MIN(3)*MIN_RR_RATIO(1.3)=3.9 → INVALID_TP
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08460, tp=1.08530,   # 4-pip SL, 3-pip TP
        entry=1.08500,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert not result.approved
    assert result.block_reason == "INVALID_TP"


def test_daily_trade_limit_blocks(monkeypatch):
    """When daily_trade_count >= MAX_TRADES_PER_DAY, validate should block."""
    monkeypatch.setattr(_config, "MAX_TRADES_PER_DAY", 5)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_trade_count=5,
    )
    assert not result.approved
    assert result.block_reason == "DAILY_TRADE_LIMIT"


def test_daily_trade_limit_not_triggered_below_max(monkeypatch):
    """daily_trade_count < MAX_TRADES_PER_DAY should not block (Gold trade)."""
    monkeypatch.setattr(_config, "MAX_TRADES_PER_DAY", 15)
    result = validate(
        action="BUY", confidence=0.8,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_trade_count=14,
    )
    assert result.approved


def test_gold_lot_formula_unaffected(monkeypatch):
    """Gold lot formula (CONTRACT_SIZE=100) must be unaffected by multi-symbol changes."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    # risk=$100, SL=$10, lot = 100/(10*100) = 0.10
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
    )
    assert result.approved
    assert result.lot_size == 0.10


def test_gold_lot_uses_contract_size(monkeypatch):
    """Gold branch: lot = risk / (sl_distance * CONTRACT_SIZE). Regression for hardcode removal."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    # risk=$100, SL=$10, lot=100/(10*100)=0.10
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
    )
    assert result.lot_size == 0.10


def test_forex_jpy_pip_size(monkeypatch):
    """JPY pairs use pip_size=0.01, not 0.0001."""
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "USDJPY")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 9.0)  # ~$9/pip for USDJPY
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    # entry=150.000, sl=149.960 (4 JPY pips = 0.04), tp=150.060 (6 JPY pips = 0.06) → ratio=1.5x ≥ 1.3 ✓
    result = validate(
        action="BUY", confidence=0.8,
        sl=149.960, tp=150.060,
        entry=150.000,
        balance=10000.0, open_trades=0, kill_switch=False,
    )
    assert result.approved


def test_daily_trade_limit_default_does_not_block():
    """Default MAX_TRADES_PER_DAY=999 should not block a normal 10-trade day."""
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_trade_count=10,
    )
    assert result.approved  # 10 < 999 default


# ── Daily Drawdown Guard ──────────────────────────────────────────────────


def test_drawdown_blocks_when_equity_below_limit(monkeypatch):
    """Equity dropped below daily_start * (1 - DAILY_DRAWDOWN_LIMIT) → DAILY_DRAWDOWN."""
    monkeypatch.setattr(_config, "DAILY_DRAWDOWN_LIMIT", 0.03)
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 10)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    # daily_start=10000, equity=9600 → -4% → exceeds 3% limit
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_start_balance=10000.0, equity=9600.0,
    )
    assert not result.approved
    assert result.block_reason == "DAILY_DRAWDOWN"


def test_drawdown_passes_when_equity_above_limit(monkeypatch):
    """Equity still within drawdown limit → trade allowed."""
    monkeypatch.setattr(_config, "DAILY_DRAWDOWN_LIMIT", 0.05)
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 10)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    # daily_start=10000, equity=9600 → -4% → within 5% limit
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_start_balance=10000.0, equity=9600.0,
    )
    assert result.approved


def test_drawdown_at_exact_boundary_passes(monkeypatch):
    """Equity exactly at threshold (not below) → trade allowed."""
    monkeypatch.setattr(_config, "DAILY_DRAWDOWN_LIMIT", 0.03)
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 10)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    # daily_start=10000, threshold=9700, equity=9700 → exactly at boundary
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_start_balance=10000.0, equity=9700.0,
    )
    assert result.approved


def test_drawdown_skipped_when_daily_start_zero(monkeypatch):
    """When daily_start_balance=0 (not yet set), drawdown check is skipped."""
    monkeypatch.setattr(_config, "DAILY_DRAWDOWN_LIMIT", 0.03)
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 10)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100.0)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    monkeypatch.setattr(_config, "MIN_SL_USD", 3.0)
    monkeypatch.setattr(_config, "MAX_SL_USD", 25.0)
    result = validate(
        action="BUY", confidence=0.9,
        sl=1910.0, tp=1940.0,
        entry=1920.0, balance=10000.0,
        open_trades=0, kill_switch=False,
        daily_start_balance=0.0, equity=9000.0,
    )
    assert result.approved


def test_drawdown_forex_3_percent(monkeypatch):
    """Forex with 3% drawdown limit blocks at -3.5%."""
    monkeypatch.setattr(_config, "DAILY_DRAWDOWN_LIMIT", 0.03)
    monkeypatch.setattr(_config, "MAX_CONCURRENT_TRADES", 10)
    monkeypatch.setattr(_config, "CONTRACT_SIZE", 100_000)
    monkeypatch.setattr(_config, "SYMBOL", "GBPUSD")
    monkeypatch.setattr(_config, "PIP_VALUE_PER_LOT", 10.0)
    monkeypatch.setattr(_config, "SL_PIPS_MIN", 3.0)
    monkeypatch.setattr(_config, "SL_PIPS_MAX", 5.0)
    monkeypatch.setattr(_config, "MIN_RR_RATIO", 1.3)
    monkeypatch.setattr(_config, "RISK_PER_TRADE", 0.01)
    # daily_start=5000, equity=4825 → -3.5% → exceeds 3%
    result = validate(
        action="BUY", confidence=0.9,
        sl=1.08460, tp=1.08560,
        entry=1.08500, balance=5000.0,
        open_trades=0, kill_switch=False,
        daily_start_balance=5000.0, equity=4825.0,
    )
    assert not result.approved
    assert result.block_reason == "DAILY_DRAWDOWN"
