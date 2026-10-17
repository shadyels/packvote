"""Integration tests for voting API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.participant import Participant
from app.models.trip import Trip
from tests.factories import make_itinerary
from tests.helpers import auth_headers as auth_headers_for
from tests.helpers import register_and_login


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
    voter_email = "voter@test.com"
    resp = await client.post(
        "/trips/",
        json={"title": "Vote Trip", "participant_emails": [voter_email]},
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

    itin1 = make_itinerary(db, trip_id, destination_name="Destination A")
    itin2 = make_itinerary(db, trip_id, destination_name="Destination B")
    await db.flush()

    # Get an invitee participant token (not the creator row)
    participant_result = await db.execute(
        select(Participant).where(
            Participant.trip_id == trip_id, Participant.user_id.is_(None)
        )
    )
    participant = participant_result.scalars().first()
    assert participant is not None

    await db.commit()

    return {
        "trip_id": trip_id,
        "token": participant.token,
        "voter_email": voter_email,
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
        assert data["participant_id"] is not None
        assert "user_id" not in data

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
        resp = await client.get(
            f"/votes/trips/{ctx['trip_id']}/results", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trip_id"] == ctx["trip_id"]
        assert data["is_complete"] is True
        assert len(data["rounds"]) > 0

    async def test_trip_not_found_returns_404(
        self, client: AsyncClient, auth_headers
    ) -> None:
        resp = await client.get("/votes/trips/99999/results", headers=auth_headers)
        assert resp.status_code == 404

    async def test_missing_trip_without_credentials_is_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/votes/trips/99999/results")
        assert resp.status_code == 401


async def _login(client: AsyncClient, email: str) -> dict:
    return auth_headers_for(await register_and_login(client, email, "test1234"))


class TestResultsAuth:
    async def test_no_credentials_401(self, client, voting_context) -> None:
        url = f"/votes/trips/{voting_context['trip_id']}/results"
        assert (await client.get(url)).status_code == 401

    async def test_unknown_participant_token_401(self, client, voting_context) -> None:
        url = f"/votes/trips/{voting_context['trip_id']}/results"
        resp = await client.get(url, headers={"X-Participant-Token": "nope"})
        assert resp.status_code == 401

    async def test_own_participant_token_200(self, client, voting_context) -> None:
        ctx = voting_context
        resp = await client.get(
            f"/votes/trips/{ctx['trip_id']}/results",
            headers={"X-Participant-Token": ctx["token"]},
        )
        assert resp.status_code == 200

    async def test_other_trips_participant_token_403(
        self, client, auth_headers, voting_context
    ) -> None:
        other = await client.post(
            "/trips/",
            json={"title": "Other", "participant_emails": ["x@test.com"]},
            headers=auth_headers,
        )
        other_id = other.json()["id"]
        resp = await client.get(
            f"/votes/trips/{other_id}/results",
            headers={"X-Participant-Token": voting_context["token"]},
        )
        assert resp.status_code == 403

    async def test_unrelated_jwt_403(self, client, voting_context) -> None:
        headers = await _login(client, "stranger@test.com")
        resp = await client.get(
            f"/votes/trips/{voting_context['trip_id']}/results", headers=headers
        )
        assert resp.status_code == 403

    async def test_creator_jwt_200(self, client, auth_headers, voting_context) -> None:
        resp = await client.get(
            f"/votes/trips/{voting_context['trip_id']}/results", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_linked_participant_jwt_200(self, client, voting_context) -> None:
        # Registering the invited email links the existing participant row.
        headers = await _login(client, voting_context["voter_email"])
        resp = await client.get(
            f"/votes/trips/{voting_context['trip_id']}/results", headers=headers
        )
        assert resp.status_code == 200


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


class TestResultsFreshness:
    async def test_results_reflect_ballots_cast_after_first_read(
        self, client: AsyncClient, auth_headers, voting_context
    ) -> None:
        ctx = voting_context
        url = f"/votes/trips/{ctx['trip_id']}/results"
        await client.post(
            f"/votes/trips/{ctx['trip_id']}/vote/{ctx['token']}",
            json={"rankings": ctx["itin_ids"]},
        )
        first = (await client.get(url, headers=auth_headers)).json()
        assert sum(first["rounds"][0]["results"].values()) == 1

        await client.post(
            f"/votes/trips/{ctx['trip_id']}/admin-vote",
            json={"rankings": ctx["itin_ids"]},
            headers=auth_headers,
        )
        second = (await client.get(url, headers=auth_headers)).json()
        assert sum(second["rounds"][0]["results"].values()) == 2
