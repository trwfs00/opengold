from src import config


def build_prompt(
    journal: str,
    regime: str,
    buy_avg: float,
    sell_avg: float,
    buy_peak: float,
    sell_peak: float,
    window_minutes: int,
    price: float,
    atr: float,
) -> str:
    """Build the Claude prompt from market context and trade journal."""
    sections = []

    if journal:
        sections.append(f"[JOURNAL]\n{journal}")

    if config.CONTRACT_SIZE >= 100_000:  # Forex
        price_str = f"{price:.5f}"
        atr_str = f"{atr:.5f}"
    else:  # Gold
        price_str = f"{price:.2f}"
        atr_str = f"{atr:.2f}"

    sections.append(
        f"[MARKET — {window_minutes}-min window]\n"
        f"Dominant regime: {regime} | Price: {price_str} | ATR(14): {atr_str}\n"
        f"Avg  — buy: {buy_avg:.1f}, sell: {sell_avg:.1f}\n"
        f"Peak — buy: {buy_peak:.1f}, sell: {sell_peak:.1f}"
    )

    if config.CONTRACT_SIZE >= 100_000:  # Forex
        role = f"expert {config.SYMBOL} forex scalper"
        rr_example_sl = config.SL_PIPS_MIN
        rr_example_tp = rr_example_sl * config.MIN_RR_RATIO
        risk_constraints = (
            f"- SL distance: {config.SL_PIPS_MIN}–{config.SL_PIPS_MAX} pips from entry\n"
            f"- TP distance: at least {config.TP_PIPS_MIN} pips from entry\n"
            f"- TP/SL ratio: at least {config.MIN_RR_RATIO} "
            f"(e.g. if SL={rr_example_sl:.0f} pips, TP must be >={rr_example_tp:.1f} pips)"
        )
    else:  # Gold
        role = f"expert gold ({config.SYMBOL}) swing trader"
        risk_constraints = (
            f"- SL distance from entry: ${config.MIN_SL_USD}–${config.MAX_SL_USD}\n"
            f"- TP distance from entry: at least ${config.MIN_TP_USD}\n"
            f"- TP/SL ratio: at least {config.MIN_RR_RATIO} "
            f"(e.g. if SL=$10, TP must be >=${10 * config.MIN_RR_RATIO:.0f})"
        )

    sections.append(
        f"[TASK]\n"
        f"You are an {role}. Based on the market context above, "
        "decide the next trade action.\n"
        "Reply with ONLY valid JSON (no markdown, no explanation):\n"
        '{"action": "BUY"|"SELL"|"SKIP", "confidence": 0.0-1.0, '
        '"sl": <stop_loss_price>, "tp": <take_profit_price>, '
        '"reasoning": "<one sentence explaining your decision>"}\n'
        f"Risk constraints (your SL/TP MUST satisfy these or the trade will be rejected):\n"
        f"{risk_constraints}\n"
        "If uncertain or conditions are unfavourable, use SKIP."
    )

    return "\n\n".join(sections)
