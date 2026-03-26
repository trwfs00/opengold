from dataclasses import dataclass


@dataclass
class Decision:
    action: str  # "BUY", "SELL", or "SKIP"
    confidence: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
