from dataclasses import dataclass

VALID_SIGNALS = {"BUY", "SELL", "NEUTRAL"}


@dataclass
class SignalResult:
    name: str
    signal: str
    confidence: float

    def __post_init__(self):
        if self.signal not in VALID_SIGNALS:
            raise ValueError(f"signal must be one of {VALID_SIGNALS}, got '{self.signal}'")
        self.confidence = max(0.0, min(1.0, self.confidence))
