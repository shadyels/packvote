"""Single source of truth for all input length/format caps."""

import math

# String field caps
TITLE_MAX = 120
DESTINATION_MAX = 100
NOTES_MAX = 2000
NAME_MAX = 80
INTERESTS_MAX = 1000
ACTIVITY_TAG_MAX = 40
ACTIVITY_TAGS_MAX_ITEMS = 20
PARTICIPANT_EMAILS_MAX = 20
PASSWORD_MIN = 8
PASSWORD_MAX = 72  # bcrypt silently truncates past 72 bytes
RANKINGS_MAX = 50

# Token budget constants for trip duration cap
# These are calibration estimates; lock from real measured completion tokens.
SAFE_OUTPUT_TOKENS = 15_000
OPTION_OVERHEAD_TOKENS = 250
PER_DAY_TOKENS = 360


def max_trip_days(num_options: int) -> int:
    """Return the maximum safe trip duration for a given num_options.

    Derived from MAX_OUTPUT_TOKENS in services/ai/openai_compat.py.
    Ensures AI output cannot be truncated due to oversized date ranges.
    """
    if num_options < 1:
        return 1
    result = math.floor(
        (SAFE_OUTPUT_TOKENS - num_options * OPTION_OVERHEAD_TOKENS)
        / (num_options * PER_DAY_TOKENS)
    )
    return max(1, result)
