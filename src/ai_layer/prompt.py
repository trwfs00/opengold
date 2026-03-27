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
        pip_size = 0.01 if "JPY" in config.SYMBOL else 0.0001
        atr_pips = round(atr / pip_size, 1)
        sl_example = round(min(max(atr_pips, config.SL_PIPS_MIN), config.SL_PIPS_MAX), 1)
        # Target 0.15x above minimum to absorb price-rounding loss (~0.4 pip per side)
        tp_target_ratio = config.MIN_RR_RATIO + 0.15
        tp_example = round(sl_example * tp_target_ratio, 1)
        role = f"expert {config.SYMBOL} forex scalper"
        risk_constraints = (
            f"- SL: {config.SL_PIPS_MIN}\u2013{config.SL_PIPS_MAX} pips from entry\n"
            f"- TP/SL ratio: minimum {config.MIN_RR_RATIO}x — AIM for {tp_target_ratio:.2f}x to avoid rounding failures\n"
            f"- Current ATR = {atr_pips} pips \u2192 use SL={sl_example} pips, TP>={tp_example} pips\n"
            f"  (NEVER set TP at exactly {config.MIN_RR_RATIO}x SL — price rounding will drop it below minimum)"
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
        "Direction rules: BUY → sl < entry < tp | SELL → tp < entry < sl\n"
        "If uncertain or conditions are unfavourable, use SKIP."
    )

    return "\n\n".join(sections)
