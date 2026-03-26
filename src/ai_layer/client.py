import json
import logging
from dataclasses import dataclass, field

import anthropic

from src import config

logger = logging.getLogger(__name__)

_VALID_ACTIONS = {"BUY", "SELL", "SKIP"}


@dataclass
class AIDecision:
    action: str
    confidence: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    reasoning: str | None = None
    error: str | None = None


def _call_model(client: anthropic.Anthropic, model: str, prompt: str) -> str:
    """Call the Anthropic API and return the raw text response."""
    message = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _parse(raw: str) -> AIDecision:
    """Parse the raw JSON response into an AIDecision.

    Handles markdown code fences, invalid action values, and malformed JSON.
    """
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"AI response is not valid JSON: {raw!r}")
        return AIDecision(action="SKIP", error="AI_PARSE_ERROR")

    action = data.get("action", "SKIP").upper()
    if action not in _VALID_ACTIONS:
        logger.warning(f"AI returned unknown action: {action!r}")
        return AIDecision(action="SKIP", error="AI_PARSE_ERROR")

    return AIDecision(
        action=action,
        confidence=float(data.get("confidence", 0.0)),
        sl=float(data.get("sl", 0.0)),
        tp=float(data.get("tp", 0.0)),
        reasoning=str(data["reasoning"]) if "reasoning" in data else None,
    )


def decide(prompt: str) -> AIDecision:
    """Call Claude Haiku (then Sonnet fallback) and parse the AI trading decision."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    models = [config.CLAUDE_PRIMARY_MODEL, config.CLAUDE_FALLBACK_MODEL]

    for model in models:
        try:
            raw = _call_model(client, model, prompt)
            return _parse(raw)
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")

    return AIDecision(action="SKIP", error="AI_API_ERROR")
