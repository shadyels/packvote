"""Unit tests for input sanitization and validation logic."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas._limits import max_trip_days
from app.schemas._sanitize import sanitize_text
from app.schemas.participant import TripAccessByCode
from app.schemas.preference import PreferenceCreate
from app.schemas.trip import TripCreate
from app.schemas.user import PasswordResetConfirm, UserCreate
from app.schemas.vote import VoteSubmit


# ---------------------------------------------------------------------------
# sanitize_text
# ---------------------------------------------------------------------------


def test_sanitize_text_strips_control_chars() -> None:
    assert sanitize_text("hello\x00world\x01") == "helloworld"


def test_sanitize_text_preserves_newlines() -> None:
    assert sanitize_text("line1\nline2") == "line1\nline2"


def test_sanitize_text_normalizes_multi_space() -> None:
    assert sanitize_text("hello   world") == "hello world"


def test_sanitize_text_strips_leading_trailing() -> None:
    assert sanitize_text("  hello  ") == "hello"


def test_sanitize_text_strips_zero_width_chars() -> None:
    # Zero-width space (U+200B) embedded in "hel​lo"
    result = sanitize_text("hel​lo")
    assert result == "hello"


# ---------------------------------------------------------------------------
# max_trip_days
# ---------------------------------------------------------------------------


def test_max_trip_days_n2_is_20() -> None:
    assert max_trip_days(2) == 20


def test_max_trip_days_n3_is_13() -> None:
    assert max_trip_days(3) == 13


def test_max_trip_days_n4_is_9() -> None:
    assert max_trip_days(4) == 9


def test_max_trip_days_n5_is_7() -> None:
    assert max_trip_days(5) == 7


# ---------------------------------------------------------------------------
# TripCreate schema
# ---------------------------------------------------------------------------

_DEFAULT_EMAILS = ["test@example.com"]


def test_trip_create_title_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        TripCreate(title="a" * 121, participant_emails=_DEFAULT_EMAILS)


def test_trip_create_empty_title_raises() -> None:
    with pytest.raises(ValidationError):
        TripCreate(title="   ", participant_emails=_DEFAULT_EMAILS)


def test_trip_create_notes_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        TripCreate(
            title="My Trip", notes="a" * 2001, participant_emails=_DEFAULT_EMAILS
        )


def test_trip_create_too_many_participant_emails_raises() -> None:
    with pytest.raises(ValidationError):
        TripCreate(
            title="My Trip",
            participant_emails=[f"user{i}@x.com" for i in range(21)],
        )


def test_trip_create_invalid_email_raises() -> None:
    with pytest.raises(ValidationError):
        TripCreate(title="My Trip", participant_emails=["not-an-email"])


def test_trip_create_date_range_exceeds_cap_raises() -> None:
    # num_options=5 → max_trip_days=7; 8-day range (Jan 1 to Jan 9) should fail
    with pytest.raises(ValidationError):
        TripCreate(
            title="My Trip",
            participant_emails=_DEFAULT_EMAILS,
            num_options=5,
            proposed_start_date=datetime(2025, 1, 1),
            proposed_end_date=datetime(2025, 1, 9),
        )


def test_trip_create_valid_passes() -> None:
    trip = TripCreate(
        title="  My Trip  ",
        participant_emails=_DEFAULT_EMAILS,
    )
    assert trip.title == "My Trip"


def test_trip_create_date_range_at_cap_passes() -> None:
    # num_options=5 → max_trip_days=7; exactly 7-day range (Jan 1 to Jan 8) should pass
    trip = TripCreate(
        title="My Trip",
        participant_emails=_DEFAULT_EMAILS,
        num_options=5,
        proposed_start_date=datetime(2025, 1, 1),
        proposed_end_date=datetime(2025, 1, 8),
    )
    assert trip.proposed_start_date is not None


# ---------------------------------------------------------------------------
# TripAccessByCode schema
# ---------------------------------------------------------------------------


def test_trip_access_invalid_trip_code_lowercase_raises() -> None:
    with pytest.raises(ValidationError):
        TripAccessByCode(trip_code="abcdefgh", pin="1234")


def test_trip_access_invalid_trip_code_short_raises() -> None:
    with pytest.raises(ValidationError):
        TripAccessByCode(trip_code="ABCD123", pin="1234")


def test_trip_access_invalid_pin_non_digits_raises() -> None:
    with pytest.raises(ValidationError):
        TripAccessByCode(trip_code="ABCD1234", pin="12ab")


def test_trip_access_invalid_pin_5_digits_raises() -> None:
    with pytest.raises(ValidationError):
        TripAccessByCode(trip_code="ABCD1234", pin="12345")


def test_trip_access_valid_passes() -> None:
    access = TripAccessByCode(trip_code="ABCD1234", pin="1234")
    assert access.trip_code == "ABCD1234"
    assert access.pin == "1234"


# ---------------------------------------------------------------------------
# UserCreate schema
# ---------------------------------------------------------------------------


def test_user_create_password_too_short_raises() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="abc")


def test_user_create_password_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="a" * 73)


def test_user_create_password_at_max_passes() -> None:
    user = UserCreate(email="user@example.com", password="a" * 72)
    assert len(user.password) == 72


def test_user_create_full_name_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", password="validpass", full_name="a" * 81)


# ---------------------------------------------------------------------------
# PasswordResetConfirm schema
# ---------------------------------------------------------------------------


def test_password_reset_confirm_too_short_raises() -> None:
    with pytest.raises(ValidationError):
        PasswordResetConfirm(token="sometoken", new_password="short")


# ---------------------------------------------------------------------------
# VoteSubmit schema
# ---------------------------------------------------------------------------


def test_vote_submit_duplicate_rankings_raises() -> None:
    with pytest.raises(ValidationError):
        VoteSubmit(rankings=[1, 2, 1])


def test_vote_submit_too_many_rankings_raises() -> None:
    with pytest.raises(ValidationError):
        VoteSubmit(rankings=list(range(51)))


def test_vote_submit_valid_passes() -> None:
    vote = VoteSubmit(rankings=[3, 1, 2])
    assert vote.rankings == [3, 1, 2]


# ---------------------------------------------------------------------------
# PreferenceCreate schema
# ---------------------------------------------------------------------------


def test_preference_create_too_many_tags_raises() -> None:
    with pytest.raises(ValidationError):
        PreferenceCreate(activity_tags=[f"tag{i}" for i in range(21)])


def test_preference_create_tag_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        PreferenceCreate(activity_tags=["a" * 41])


def test_preference_create_invalid_currency_raises() -> None:
    with pytest.raises(ValidationError):
        PreferenceCreate(currency="usd")


def test_preference_create_valid_passes() -> None:
    pref = PreferenceCreate(
        name="Alice", currency="USD", activity_tags=["hiking", "food"]
    )
    assert pref.name == "Alice"
    assert pref.currency == "USD"
    assert pref.activity_tags == ["hiking", "food"]
