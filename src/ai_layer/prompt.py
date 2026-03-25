def build_prompt(
    journal: str,
    regime: str,
    buy_score: float,
    sell_score: float,
    price: float,
    atr: float,
) -> str:
    """Build the Claude prompt from market context and trade journal."""
    sections = []

    if journal:
        sections.append(f"[JOURNAL]\n{journal}")

    sections.append(
        f"[MARKET]\n"
        f"Regime: {regime} | Buy score: {buy_score:.1f} | Sell score: {sell_score:.1f}\n"
        f"Price: {price:.2f} | ATR(14): {atr:.2f}"
    )

    sections.append(
        "[TASK]\n"
        "You are an expert gold (XAU/USD) trader. Based on the market context above, "
        "decide the next trade action.\n"
        "Reply with ONLY valid JSON (no markdown, no explanation):\n"
        '{"action": "BUY"|"SELL"|"SKIP", "confidence": 0.0-1.0, '
        '"sl": <stop_loss_price>, "tp": <take_profit_price>}\n'
        "If uncertain or conditions are unfavourable, use SKIP."
    )

    return "\n\n".join(sections)
