import logging
from src.db import execute
from src import config

logger = logging.getLogger(__name__)

_QUERY = """
    SELECT
        t.open_time, t.direction, d.regime,
        d.buy_score, d.sell_score,
        t.pnl, t.result, t.sl, t.tp
    FROM trades t
    LEFT JOIN LATERAL (
        SELECT regime, buy_score, sell_score
        FROM decisions
        WHERE time <= t.open_time
        ORDER BY time DESC
        LIMIT 1
    ) d ON TRUE
    ORDER BY t.open_time DESC
    LIMIT %s
"""


def get_journal_context(n: int | None = None) -> str:
    """Fetch the last n closed trades and return a compact journal string.

    Returns an empty string if no trades exist (caller omits the journal section).
    n defaults to config.JOURNAL_TRADE_COUNT.
    """
    if n is None:
        n = config.JOURNAL_TRADE_COUNT
    try:
        rows = execute(_QUERY, (n,), fetch=True) or []
    except Exception as e:
        logger.error(f"journal fetch failed: {e}")
        return ""

    if not rows:
        return ""

    lines = []
    wins = 0
    total_win_pnl = 0.0
    total_loss_pnl = 0.0

    for i, row in enumerate(rows, 1):
        _, direction, regime, buy_score, sell_score, pnl, result, sl, tp = row
        buy_score = buy_score or 0.0   # guard NULL from LEFT JOIN
        sell_score = sell_score or 0.0
        regime_str = regime or "UNKNOWN"
        result_str = result or "UNKNOWN"
        sign = "+" if pnl >= 0 else "-"          # sign BEFORE dollar sign
        pnl_str = f"{sign}${abs(pnl):.0f}"
        lines.append(
            f"[{i}] {direction:<4} {regime_str:<8} "
            f"buy={buy_score:.1f} sell={sell_score:.1f} "
            f"\u2192 {result_str:<8} {pnl_str:<8} "
            f"(SL={sl} TP={tp})"
        )
        if result == "WIN":
            wins += 1
            total_win_pnl += pnl
        elif result == "LOSS":
            total_loss_pnl += abs(pnl)

    total = len(rows)
    avg_win = total_win_pnl / wins if wins else 0.0
    losses = total - wins
    avg_loss = total_loss_pnl / losses if losses else 0.0
    net = sum(r[5] for r in rows)

    net_sign = "+" if net >= 0 else "-"
    net_str = f"{net_sign}${abs(net):.0f}"
    summary = (
        f"Win rate: {wins}/{total} | "
        f"Avg win: ${avg_win:.0f} | "
        f"Avg loss: ${avg_loss:.0f} | "
        f"Net: {net_str}"
    )
    header = f"RECENT TRADES (last {total}):"
    return "\n".join([header] + lines + [summary])
