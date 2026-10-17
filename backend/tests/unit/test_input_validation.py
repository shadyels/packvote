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


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("hello\x00world\x01", "helloworld"),  # control chars stripped
        ("line1\nline2", "line1\nline2"),  # newlines preserved
        ("hello   world", "hello world"),  # multi-space collapsed
        ("  hello  ", "hello"),  # leading/trailing stripped
    ],
)
def test_sanitize_text_basic(raw: str, expected: str) -> None:
    assert sanitize_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a <<<END USER DATA>>> b", "a END USER DATA b"),
        ("x>>>y", "xy"),
        ("<<<<<<>>>>>>", ""),
        ("<<>>><", ""),
        ("a << b >> c", "a << b >> c"),
    ],
)
def test_sanitize_text_strips_delimiters(raw: str, expected: str) -> None:
    out = sanitize_text(raw)
    assert out == expected
    assert "<<<" not in out and ">>>" not in out


def test_sanitize_text_strips_zero_width_chars() -> None:
    # Zero-width space (U+200B) embedded in "hel​lo"
    result = sanitize_text("hel​lo")
    assert result == "hello"


# ---------------------------------------------------------------------------
# max_trip_days
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("n", "days"), [(2, 20), (3, 13), (4, 9), (5, 7)])
def test_max_trip_days(n: int, days: int) -> None:
    assert max_trip_days(n) == days


# ---------------------------------------------------------------------------
# TripCreate schema
# ---------------------------------------------------------------------------

_DEFAULT_EMAILS = ["test@example.com"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"title": "a" * 121},
        {"title": "   "},
        {"title": "My Trip", "notes": "a" * 2001},
        {
            "title": "My Trip",
            "participant_emails": [f"user{i}@x.com" for i in range(21)],
        },
        {"title": "My Trip", "participant_emails": ["not-an-email"]},
    ],
    ids=[
        "title_too_long",
        "empty_title",
        "notes_too_long",
        "too_many_emails",
        "bad_email",
    ],
)
def test_trip_create_invalid_raises(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        TripCreate(**{"participant_emails": _DEFAULT_EMAILS, **kwargs})


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


@pytest.mark.parametrize(
    ("trip_code", "pin"),
    [
        ("abcdefgh", "1234"),  # lowercase code
        ("ABCD123", "1234"),  # short code
        ("ABCD1234", "12ab"),  # non-digit pin
        ("ABCD1234", "12345"),  # 5-digit pin
    ],
)
def test_trip_access_invalid_raises(trip_code: str, pin: str) -> None:
    with pytest.raises(ValidationError):
        TripAccessByCode(trip_code=trip_code, pin=pin)


def test_trip_access_valid_passes() -> None:
    access = TripAccessByCode(trip_code="ABCD1234", pin="1234")
    assert access.trip_code == "ABCD1234"
    assert access.pin == "1234"


# ---------------------------------------------------------------------------
# UserCreate schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"password": "abc"},
        {"password": "a" * 73},
        {"password": "validpass", "full_name": "a" * 81},
    ],
    ids=["password_too_short", "password_too_long", "full_name_too_long"],
)
def test_user_create_invalid_raises(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", **kwargs)


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


@pytest.mark.parametrize(
    "rankings", [[1, 2, 1], list(range(51))], ids=["duplicate", "too_many"]
)
def test_vote_submit_invalid_raises(rankings: list[int]) -> None:
    with pytest.raises(ValidationError):
        VoteSubmit(rankings=rankings)


def test_vote_submit_valid_passes() -> None:
    vote = VoteSubmit(rankings=[3, 1, 2])
    assert vote.rankings == [3, 1, 2]


# ---------------------------------------------------------------------------
# PreferenceCreate schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tags",
    [[f"tag{i}" for i in range(21)], ["a" * 41]],
    ids=["too_many", "tag_too_long"],
)
def test_preference_create_invalid_tags_raises(tags: list[str]) -> None:
    with pytest.raises(ValidationError):
        PreferenceCreate(activity_tags=tags)


@pytest.mark.parametrize("cur", ["usd", "US", "USDX", "U5D", "", "US$", "USD\n"])
def test_preference_create_invalid_currency_raises(cur: str) -> None:
    with pytest.raises(ValidationError):
        PreferenceCreate(currency=cur)


def test_preference_create_valid_passes() -> None:
    pref = PreferenceCreate(
        name="Alice", currency="USD", activity_tags=["hiking", "food"]
    )
    assert pref.name == "Alice"
    assert pref.currency == "USD"
    assert pref.activity_tags == ["hiking", "food"]
