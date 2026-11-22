"""Deterministic pass/fail checks on one raw model response."""

from typing import Any

from pydantic import ValidationError

from app.schemas.itinerary import TIME_SLOTS, AIGenerationResponse
from app.services.ai.json_utils import AIParseError, extract_json

# budget_in_range is deliberately absent: the prompt never says whether a
# participant's budget is per person or for the whole trip, so there is no
# single range a total_estimated_budget could be held to.
CHECKS = (
    "json_valid",
    "schema_valid",
    "option_count",
    "day_count",
    "time_field",
    "time_slots",
)
# Reported but kept out of all_checks_pass_rate: v3 is told to leave times null,
# so it can never pass the v4 feature check by following its own prompt.
INFORMATIONAL = frozenset({"time_slots"})


def check(
    raw: str, case: dict, duration: int, num_options: int, slots_required: bool
) -> dict[str, bool]:
    """Run every check; destination_respected only for fixed-destination cases.

    time_field: did the response follow its own prompt's time rule (every time a
    valid slot when slots_required, else every time null).
    """
    destination = case["trip"].get("destination")
    try:
        data = extract_json(raw)
    except AIParseError:
        data = None
    options = _options(data)

    try:
        AIGenerationResponse.model_validate(data)
        schema_valid = True
    except ValidationError:
        schema_valid = False

    # Raw values on purpose: DailyActivity coerces any bad slot to None.
    days = [d for o in options for d in _list(o.get("daily_itinerary"))]
    acts = [a for d in days for a in _list(_dict(d).get("activities"))]

    results = {
        "json_valid": data is not None,
        "schema_valid": schema_valid,
        "option_count": len(options) == num_options,
        "day_count": bool(options)
        and all(len(_list(o.get("daily_itinerary"))) == duration for o in options),
        "time_field": bool(acts)
        and all(
            (_dict(a).get("time") in TIME_SLOTS)
            if slots_required
            else (_dict(a).get("time") is None)
            for a in acts
        ),
        "time_slots": bool(acts)
        and all(_dict(a).get("time") in TIME_SLOTS for a in acts),
    }
    if destination:
        city = destination.split(",")[0].strip().lower()
        results["destination_respected"] = bool(options) and all(
            city in str(o.get("destination_name", "")).lower() for o in options
        )
    return results


def _dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _list(v: Any) -> list:
    return v if isinstance(v, list) else []


def _options(data: dict | None) -> list[dict]:
    return [o for o in _list(_dict(data).get("options")) if isinstance(o, dict)]
