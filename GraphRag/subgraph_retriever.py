from __future__ import annotations

import json
import re
from typing import Callable

SEED_PROMPT = """You extract ontology-relevant terms from a network intent.
Output a JSON array of short English terms (1-3 words each), no commentary.
Cover: metric (e.g. latency, packet loss), statistic (p95, p99, average),
scope (hub to all spokes, per spoke, specific spoke), measurement method (TWAMP),
time window (5 minute, hourly, monthly).
Skip tenant names, site names, numbers, and units."""


def _strip_code_fence(text: str) -> str:
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```\s*$", text.strip(), re.DOTALL)
    if fence:
        return fence.group(1)
    return text


def extract_seeds(nl_intent: str, caller: Callable[[str], str]) -> list[str]:
    """Call LLM (via injected caller) to extract a list of ontology seed terms."""
    user_msg = f"{SEED_PROMPT}\n\nIntent: {nl_intent}"
    raw = caller(user_msg)
    raw = _strip_code_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, (str, int, float))]
