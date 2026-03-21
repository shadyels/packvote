"""Integration tests for voting API endpoints."""

from __future__ import annotations

import json
import secrets
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip


@pytest.fixture
async def voting_context(
    client: AsyncClient,
    db: AsyncSession,
    auth_headers,
    mock_email,
    mock_session_factory,
):
    """
    Create a trip with 1 participant, 2 itineraries in VOTING status.
    Returns dict with trip, participant token, itinerary IDs.
    """
    resp = await client.post(
        "/trips/",
        json={"title": "Vote Trip", "participant_emails": ["voter@test.com"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    trip_data = resp.json()
    trip_id = trip_data["id"]

    # Put the trip in VOTING status with iteration 1 and add itineraries directly to DB
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one()
    trip.status = "VOTING"
    trip.current_iteration = 1

    itin1 = Itinerary(
        trip_id=trip_id,
        iteration_number=1,
        destination_name="Destination A",
        destination_description="Desc A",
        daily_itinerary_json=json.dumps([]),
        total_estimated_budget=1000.0,
        currency="USD",
        match_reasoning="reason",
        highlights=json.dumps(["h1"]),
    )
    itin2 = Itinerary(
        trip_id=trip_id,
        iteration_number=1,
        destination_name="Destination B",
        destination_description="Desc B",
        daily_itinerary_json=json.dumps([]),
        total_estimated_budget=1200.0,
        currency="USD",
        match_reasoning="reason",
        highlights=json.dumps(["h2"]),
    )
    db.add(itin1)
    db.add(itin2)
    await db.flush()

    # Get participant token
    participant_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip_id)
    )
    participant = participant_result.scalars().first()
    assert participant is not None

    await db.commit()

    return {
        "trip_id": trip_id,
        "token": participant.token,
        "itin_ids": [itin1.id, itin2.id],
    }


# ---------------------------------------------------------------------------
# POST /votes/trips/{id}/vote/{token}
# ---------------------------------------------------------------------------


class TestSubmitVote:
    async def test_returns_201(self, client: AsyncClient, voting_context) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/votes/trips/{ctx['trip_id']}/vote/{ctx['token']}",
            json={"rankings": ctx["itin_ids"]},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["trip_id"] == ctx["trip_id"]
        assert data["participant_id"] is not None

    async def test_invalid_token_returns_404(
        self, client: AsyncClient, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/votes/trips/{ctx['trip_id']}/vote/bad-token",
            json={"rankings": ctx["itin_ids"]},
        )
        assert resp.status_code == 404

    async def test_wrong_trip_returns_403(
        self, client: AsyncClient, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/votes/trips/99999/vote/{ctx['token']}",
            json={"rankings": ctx["itin_ids"]},
        )
        # Participant exists but doesn't belong to trip 99999 → 403
        assert resp.status_code == 403

    async def test_not_voting_status_returns_409(
        self, client: AsyncClient, db: AsyncSession, voting_context
    ) -> None:
        ctx = voting_context
        trip_result = await db.execute(select(Trip).where(Trip.id == ctx["trip_id"]))
        trip = trip_result.scalar_one()
        trip.status = "COLLECTING_PREFERENCES"
        await db.commit()

        resp = await client.post(
            f"/votes/trips/{ctx['trip_id']}/vote/{ctx['token']}",
            json={"rankings": ctx["itin_ids"]},
        )
        assert resp.status_code == 409

    async def test_incomplete_rankings_returns_422(
        self, client: AsyncClient, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/votes/trips/{ctx['trip_id']}/vote/{ctx['token']}",
            json={"rankings": [ctx["itin_ids"][0]]},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /votes/trips/{id}/admin-vote
# ---------------------------------------------------------------------------


class TestAdminVote:
    async def test_admin_can_vote(
        self, client: AsyncClient, auth_headers, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/votes/trips/{ctx['trip_id']}/admin-vote",
            json={"rankings": ctx["itin_ids"]},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] is not None
        assert data["participant_id"] is None

    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/votes/trips/{ctx['trip_id']}/admin-vote",
            json={"rankings": ctx["itin_ids"]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /votes/trips/{id}/results
# ---------------------------------------------------------------------------


class TestGetResults:
    async def test_returns_results(
        self, client: AsyncClient, auth_headers, voting_context
    ) -> None:
        ctx = voting_context
        # Submit both votes so tally runs
        await client.post(
            f"/votes/trips/{ctx['trip_id']}/vote/{ctx['token']}",
            json={"rankings": ctx["itin_ids"]},
        )
        await client.post(
            f"/votes/trips/{ctx['trip_id']}/admin-vote",
            json={"rankings": ctx["itin_ids"]},
            headers=auth_headers,
        )
        resp = await client.get(f"/votes/trips/{ctx['trip_id']}/results")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trip_id"] == ctx["trip_id"]
        assert data["is_complete"] is True
        assert len(data["rounds"]) > 0

    async def test_trip_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/votes/trips/99999/results")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /trips/{id}/pick-winner
# ---------------------------------------------------------------------------


class TestPickWinner:
    async def test_finalize_trip(
        self, client: AsyncClient, auth_headers, voting_context
    ) -> None:
        ctx = voting_context
        itin_id = ctx["itin_ids"][0]
        resp = await client.post(
            f"/trips/{ctx['trip_id']}/pick-winner",
            json={"itinerary_id": itin_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "finalized"
        assert data["winner_itinerary_id"] == itin_id

    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(
            f"/trips/{ctx['trip_id']}/pick-winner",
            json={"itinerary_id": ctx["itin_ids"][0]},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /trips/{id}/new-iteration
# ---------------------------------------------------------------------------


class TestNewIteration:
    async def test_returns_202(
        self, client: AsyncClient, auth_headers, voting_context, mock_session_factory
    ) -> None:
        ctx = voting_context
        # Patch the generation module directly (run_generation is imported lazily inside service)
        with patch("app.services.generation.run_generation", new_callable=AsyncMock):
            resp = await client.post(
                f"/trips/{ctx['trip_id']}/new-iteration",
                headers=auth_headers,
            )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"

    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, voting_context
    ) -> None:
        ctx = voting_context
        resp = await client.post(f"/trips/{ctx['trip_id']}/new-iteration")
        assert resp.status_code == 401
