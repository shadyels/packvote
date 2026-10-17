"""Reusable text sanitizer for user-controlled input fields."""

import re
import unicodedata

# Zero-width and invisible Unicode characters to strip
_ZERO_WIDTH = re.compile(r"[​-‏‪-‮⁠-⁯﻿­]")

# Sequences of whitespace (excluding newlines) → single space
_MULTI_SPACE = re.compile(r"[^\S\n]+")

# USER DATA block delimiter tokens (runs of 3+ angle brackets)
_DELIMS = re.compile(r"<{3,}|>{3,}")


def sanitize_text(s: str) -> str:
    """Strip control chars, zero-width chars, and normalize whitespace.

    Preserves newlines (important for notes/interests fields).
    Applied before injecting user text into AI prompts to prevent
    structural manipulation via invisible chars or excessive whitespace.
    """
    # Remove control characters (except tab, newline, carriage return)
    s = "".join(
        ch for ch in s if unicodedata.category(ch)[0] != "C" or ch in ("\t", "\n", "\r")
    )
    # Strip zero-width / invisible Unicode
    s = _ZERO_WIDTH.sub("", s)
    # Normalize multi-space runs (not newlines)
    s = _MULTI_SPACE.sub(" ", s)
    # Neutralise <<< / >>> so user text can't close the USER DATA block;
    # loop because removal can splice e.g. "<<" + ">>>" + "<" into "<<<".
    while (t := _DELIMS.sub("", s)) != s:
        s = t
    return s.strip()
