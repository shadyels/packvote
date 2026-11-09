"""Unit tests for app/schemas/itinerary.py."""

from __future__ import annotations

import pytest

from app.schemas.itinerary import DailyActivity


class TestDailyActivityTime:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("evening", "evening"),
            (" Morning ", "morning"),
            ("09:00", None),  # pre-v4 stored clock time
            ("mornin", None),  # AI typo must not fail generation
            (5, None),  # non-string
            (None, None),
        ],
        ids=["valid", "normalised", "clock_time", "typo", "non_string", "none"],
    )
    def test_time_slot(self, raw: object, expected: str | None) -> None:
        a = DailyActivity.model_validate(
            {"time": raw, "title": "t", "description": "d"}
        )
        assert a.time == expected

    def test_missing_time_defaults_to_none(self) -> None:
        a = DailyActivity.model_validate({"title": "t", "description": "d"})
        assert a.time is None
