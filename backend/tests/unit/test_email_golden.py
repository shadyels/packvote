"""Characterisation: exact subject/body per trip-email kind (links included)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.email.brevo import EmailService

TAIL = "Or enter Trip Code: ABCD1234  PIN: 1234\n"
GOLDEN = {
    "invitation": (
        "You're invited to Summer",
        "Hi Al,\n\nYou've been invited to join the trip: Summer\n\n"
        "Join via link: https://pv.test/join/tok\n" + TAIL,
    ),
    "voting": (
        "Vote now: Summer itineraries are ready",
        "Hi Al,\n\nThe itineraries for Summer are ready. Cast your vote!\n\n"
        "Vote via link: https://pv.test/trip/tok/vote\n" + TAIL,
    ),
    "new_iteration": (
        "New options for Summer — vote again!",
        "Hi Al,\n\nA new round of itineraries has been generated for Summer.\n"
        "Check out the new options and cast your vote!\n\n"
        "Vote via link: https://pv.test/trip/tok/vote\n" + TAIL,
    ),
    "finalized": (
        "Trip finalized: Summer — Bali",
        "Hi Al,\n\nYour group has chosen: Bali!\nThe trip Summer has been finalized.\n\n"
        "View the itinerary: https://pv.test/trip/tok\n" + TAIL,
    ),
}


@pytest.mark.parametrize("kind", list(GOLDEN))
async def test_trip_email_golden(kind: str) -> None:
    svc = EmailService("k", "https://pv.test", "f@pv.test")
    with patch.object(EmailService, "_send", new=AsyncMock(return_value=True)) as send:
        await _call(svc, kind)
    assert send.call_args.kwargs == {
        "to_email": "a@a.com",
        "subject": GOLDEN[kind][0],
        "body": GOLDEN[kind][1],
    }


async def _call(svc: EmailService, kind: str) -> bool:
    return await svc.send_trip_email(
        kind,  # type: ignore[arg-type]
        to_email="a@a.com",
        participant_name="Al",
        trip_title="Summer",
        trip_code="ABCD1234",
        pin="1234",
        token="tok",
        destination_name="Bali",
    )
