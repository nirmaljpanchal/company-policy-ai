import re
from dataclasses import dataclass


@dataclass
class InjectionResult:
    blocked: bool
    reason: str = ""


# Injection/jailbreak detection patterns (case-insensitive)
INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|prior|all\s+previous)\s+instructions",
    r"disregard\s+(the\s+system\s+prompt|instructions|rules)",
    r"you\s+are\s+now",
    r"developer\s+mode",
    r"reveal\s+(your\s+system\s+prompt|the\s+system\s+prompt|prompt)",
    r"act\s+as",
    r"pretend\s+to\s+be",
    r"what\s+are\s+your\s+(instructions|instructions|system\s+prompt)",
    r"show\s+me\s+(your\s+instructions|the\s+system\s+prompt)",
    r"jailbreak",
    r"bypass",
]

# Max length for input (prevent DoS)
MAX_INPUT_LENGTH = 5000

# Threshold for special characters (heuristic for obfuscation)
SPECIAL_CHAR_THRESHOLD = 0.3


def screen_input(text: str) -> InjectionResult:
    """Screen input for injection/jailbreak attempts."""
    if len(text) > MAX_INPUT_LENGTH:
        return InjectionResult(
            blocked=True,
            reason=f"Input exceeds maximum length of {MAX_INPUT_LENGTH}"
        )

    lower_text = text.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_text):
            return InjectionResult(
                blocked=True,
                reason=f"Detected potential injection attempt: {pattern}"
            )

    special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
    special_ratio = special_count / len(text) if text else 0
    if special_ratio > SPECIAL_CHAR_THRESHOLD:
        return InjectionResult(
            blocked=True,
            reason="Excessive special characters detected"
        )

    return InjectionResult(blocked=False)


def sanitize_context(text: str) -> str:
    """Neutralize instruction-like lines in retrieved chunks."""
    lines = text.split("\n")
    sanitized = []

    for line in lines:
        lower_line = line.lower().strip()
        is_instruction = any([
            lower_line.startswith(("note:", "warning:", "caution:", "important:")),
            "only answer from" in lower_line,
            "do not" in lower_line and "mention" in lower_line,
            "remember" in lower_line and "instructions" in lower_line,
        ])

        if is_instruction:
            sanitized.append(f"[DATA]: {line}")
        else:
            sanitized.append(line)

    return "\n".join(sanitized)
