"""Unit tests for services/email_resend.py status -> email-type routing."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.participant import Participant
from app.models.trip import Trip
from app.services.email_resend import resend_emails_for_trip
from tests.factories import make_itinerary


@pytest.fixture
async def trip_ctx(client: AsyncClient, auth_headers, mock_email, db: AsyncSession):
    resp = await client.post(
        "/trips/",
        json={"title": "T", "participant_emails": ["a@x.com", "b@x.com"]},
        headers=auth_headers,
    )
    trip = (
        await db.execute(select(Trip).where(Trip.id == resp.json()["id"]))
    ).scalar_one()
    parts = list(
        (await db.execute(select(Participant).where(Participant.trip_id == trip.id)))
        .scalars()
        .all()
    )
    mock_email.sent.clear()
    return trip, parts


class TestResendStatusBranches:
    async def test_voting_first_iteration_sends_voting_notification(
        self, trip_ctx, db, mock_email
    ):
        trip, parts = trip_ctx
        trip.status, trip.current_iteration = "VOTING", 1
        sent, failed = await resend_emails_for_trip(trip, parts, db, mock_email)
        assert (sent, failed) == (len(parts), 0)
        assert {e["type"] for e in mock_email.sent} == {"voting"}

    async def test_voting_later_iteration_sends_new_iteration(
        self, trip_ctx, db, mock_email
    ):
        trip, parts = trip_ctx
        trip.status, trip.current_iteration = "VOTING", 2
        await resend_emails_for_trip(trip, parts, db, mock_email)
        assert {e["type"] for e in mock_email.sent} == {"new_iteration"}

    async def test_finalized_sends_finalized_with_destination(
        self, trip_ctx, db, mock_email
    ):
        trip, parts = trip_ctx
        itin = make_itinerary(db, trip, destination_name="Lisbon")
        await db.flush()
        trip.status, trip.winner_itinerary_id = "FINALIZED", itin.id
        sent, failed = await resend_emails_for_trip(trip, parts, db, mock_email)
        assert (sent, failed) == (len(parts), 0)
        assert {e["type"] for e in mock_email.sent} == {"finalized"}
        assert {e["destination_name"] for e in mock_email.sent} == {"Lisbon"}

    async def test_finalized_without_winner_raises(self, trip_ctx, db, mock_email):
        trip, parts = trip_ctx
        trip.status, trip.winner_itinerary_id = "FINALIZED", None
        with pytest.raises(ValueError):
            await resend_emails_for_trip(trip, parts, db, mock_email)
