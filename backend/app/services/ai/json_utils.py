"""Utilities for extracting JSON from AI model responses.

AI models sometimes wrap JSON in markdown code fences or include preamble text
even when `response_format={"type": "json_object"}` is set. This module provides
a robust extraction function that handles those cases.
"""

from __future__ import annotations

import json
import re


class AIParseError(Exception):
    """Raised when an AI response cannot be parsed as valid JSON.

    Carries the raw response text so callers can log it for debugging.
    """

    def __init__(self, message: str, raw_text: str | None = None) -> None:
        super().__init__(message)
        self.raw_text = raw_text


class AIInputError(AIParseError):
    """Raised when the AI reports the trip input is invalid.

    The AI itself diagnosed the problem (bad destination, contradictory constraints, etc.)
    and returned a structured error envelope instead of itineraries.
    Carries an actionable user-facing message and a suggestion for how to fix the input.
    """

    def __init__(
        self, message: str, suggestion: str = "", field: str = "general"
    ) -> None:
        super().__init__(message)
        self.ai_message = message
        self.suggestion = suggestion
        self.field = field  # "destination" | "dates" | "budget" | "general"


def extract_json(raw: str | None) -> dict:
    """Extract a JSON object from an AI model response string.

    Handles three common AI output patterns:
    1. Clean JSON  — ``{"options": [...]}``
    2. Fenced JSON — `` ```json\\n{...}\\n``` ``
    3. Preamble    — ``"Here is the result:\\n{...}"``

    Raises:
        AIParseError: If no valid JSON object can be extracted.
    """
    if not raw:
        raise AIParseError("AI returned empty/null content", raw_text=raw)

    # Attempt 1: direct parse (fastest path, handles well-behaved models)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    # Attempt 2: strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Attempt 3: find outermost { ... } substring
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    raise AIParseError(
        f"Could not extract JSON from AI response. First 200 chars: {raw[:200]!r}",
        raw_text=raw,
    )
