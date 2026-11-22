import copy
import json

from evals.checks import check

CASE_OPEN = {"trip": {"destination": None}}
CASE_FIXED = {"trip": {"destination": "Lisbon, Portugal"}}


def _activity(time="morning") -> dict:
    return {"time": time, "title": "Alfama walk", "description": "Steep and lovely."}


def _option(days: int = 2, destination: str = "Lisbon, Portugal") -> dict:
    return {
        "option_title": "Tiles & Trams",
        "destination_name": destination,
        "destination_description": "A hilly city.",
        "daily_itinerary": [
            {"day_number": d, "title": f"Day {d}", "activities": [_activity()]}
            for d in range(1, days + 1)
        ],
        "total_estimated_budget": 1200.0,
        "currency": "EUR",
        "match_reasoning": "Fits.",
        "highlights": ["trams"],
    }


def _good(options: int = 2, days: int = 2) -> dict:
    return {"options": [_option(days) for _ in range(options)]}


def _run(
    payload, case=CASE_FIXED, duration=2, num_options=2, slots_required=True
) -> dict[str, bool]:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return check(raw, case, duration, num_options, slots_required)


def _with_time(value) -> dict:
    payload = copy.deepcopy(_good())
    payload["options"][1]["daily_itinerary"][0]["activities"][0]["time"] = value
    return payload


def test_good_fixture_passes_everything() -> None:
    result = _run(_good())
    assert set(result) == {
        "json_valid",
        "schema_valid",
        "option_count",
        "day_count",
        "time_field",
        "time_slots",
        "destination_respected",
    }
    assert all(result.values())


def test_destination_check_only_for_fixed_destination_cases() -> None:
    assert "destination_respected" not in _run(_good(), case=CASE_OPEN)


def test_destination_ignored_fails() -> None:
    bad = {"options": [_option(destination="Porto, Portugal"), _option()]}
    result = _run(bad)
    assert result["destination_respected"] is False
    assert result["schema_valid"] is True


def test_non_json_fails_json_valid() -> None:
    result = _run("Sure! Here are your itineraries.")
    assert result["json_valid"] is False
    assert not any(result.values())


def test_wrong_day_count_fails() -> None:
    result = _run(_good(days=3), duration=2)
    assert result["day_count"] is False and result["schema_valid"] is True


def test_wrong_option_count_fails() -> None:
    result = _run(_good(options=3), num_options=2)
    assert result["option_count"] is False and result["day_count"] is True


def test_v4_bad_time_slots_fail_both_time_checks() -> None:
    # The schema coerces these to None instead of rejecting, so schema_valid
    # stays True: only the raw-JSON time checks can tell v3 from v4.
    for bad in ("09:00", None, "brunch", 9):
        result = _run(_with_time(bad))
        assert result["time_slots"] is False, bad
        assert result["time_field"] is False, bad
        assert result["schema_valid"] is True, bad


def test_v3_all_null_times_follow_instruction_but_lack_slots() -> None:
    payload = _good()
    for o in payload["options"]:
        for d in o["daily_itinerary"]:
            for a in d["activities"]:
                a["time"] = None
    result = _run(payload, slots_required=False)
    assert result["time_field"] is True
    assert result["time_slots"] is False


def test_v3_with_a_slot_fails_time_field() -> None:
    payload = _good()
    for o in payload["options"]:
        for d in o["daily_itinerary"]:
            for a in d["activities"]:
                a["time"] = None
    payload["options"][0]["daily_itinerary"][0]["activities"][0]["time"] = "morning"
    result = _run(payload, slots_required=False)
    assert result["time_field"] is False
    assert result["time_slots"] is False


def test_v4_all_slots_pass_time_field() -> None:
    result = _run(_good(), slots_required=True)
    assert result["time_field"] is True and result["time_slots"] is True


def test_error_envelope_fails_schema() -> None:
    result = _run({"error": {"message": "no", "suggestion": "x", "field": "general"}})
    assert result["json_valid"] is True
    assert result["schema_valid"] is False
    assert result["option_count"] is False
