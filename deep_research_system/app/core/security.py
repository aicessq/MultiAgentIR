from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
ID_CARD_PATTERN = re.compile(r"\d{17}[\dXx]")


def redact_pii(text: str) -> str:
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    text = ID_CARD_PATTERN.sub("[ID_REDACTED]", text)
    return text


def detect_injection(text: str) -> bool:
    suspicious_patterns = [
        "ignore previous instructions",
        "ignore all instructions",
        "you are now",
        "system prompt",
        "reveal your instructions",
    ]
    lower = text.lower()
    for pattern in suspicious_patterns:
        if pattern in lower:
            logger.warning(f"Suspicious injection pattern detected: {pattern}")
            return True
    return False
