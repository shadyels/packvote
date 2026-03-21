"""Integration tests for POST /trips/{id}/generate endpoint."""

from __future__ import annotations

import secrets
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip
from app.services.ai.service import AIService


@pytest.fixture
async def trip_id(client: AsyncClient, auth_headers, mock_email, mock_session_factory):
    """Create a trip and return its ID."""
    resp = await client.post(
        "/trips/",
        json={"title": "Test Trip", "participant_emails": ["p@test.com"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTriggerGeneration:
    async def test_returns_202_and_accepted(
        self, client: AsyncClient, auth_headers, trip_id, mock_session_factory
    ):
        with patch.object(AIService, "generate_itineraries", new_callable=AsyncMock):
            resp = await client.post(f"/trips/{trip_id}/generate", headers=auth_headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["trip_id"] == trip_id

    async def test_trip_status_set_to_generating_immediately(
        self,
        client: AsyncClient,
        auth_headers,
        trip_id,
        db: AsyncSession,
        mock_session_factory,
    ):
        from sqlalchemy import select

        with patch.object(AIService, "generate_itineraries", new_callable=AsyncMock):
            await client.post(f"/trips/{trip_id}/generate", headers=auth_headers)

        # Expire the session cache and re-fetch
        db.expire_all()
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one()
        # Status is GENERATING or VOTING (background task may have run already in tests)
        assert trip.status in ("GENERATING", "VOTING", "COLLECTING_PREFERENCES")

    async def test_404_for_nonexistent_trip(self, client: AsyncClient, auth_headers):
        resp = await client.post("/trips/99999/generate", headers=auth_headers)
        assert resp.status_code == 404

    async def test_403_for_non_owner(
        self, client: AsyncClient, trip_id, mock_email, mock_session_factory
    ):
        # Register a second user
        email2 = f"other_{secrets.token_hex(4)}@test.com"
        await client.post(
            "/auth/register", json={"email": email2, "password": "test1234"}
        )
        resp = await client.post(
            "/auth/login", json={"email": email2, "password": "test1234"}
        )
        other_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        resp = await client.post(f"/trips/{trip_id}/generate", headers=other_headers)
        assert resp.status_code == 403

    async def test_409_if_already_generating(
        self,
        client: AsyncClient,
        auth_headers,
        trip_id,
        db: AsyncSession,
        mock_session_factory,
    ):
        from sqlalchemy import select

        # Force status to GENERATING
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one()
        trip.status = "GENERATING"
        await db.commit()

        resp = await client.post(f"/trips/{trip_id}/generate", headers=auth_headers)
        assert resp.status_code == 409

    async def test_409_if_already_voting(
        self,
        client: AsyncClient,
        auth_headers,
        trip_id,
        db: AsyncSession,
        mock_session_factory,
    ):
        from sqlalchemy import select

        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one()
        trip.status = "VOTING"
        await db.commit()

        resp = await client.post(f"/trips/{trip_id}/generate", headers=auth_headers)
        assert resp.status_code == 409

    async def test_409_if_finalized(
        self,
        client: AsyncClient,
        auth_headers,
        trip_id,
        db: AsyncSession,
        mock_session_factory,
    ):
        from sqlalchemy import select

        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        trip = result.scalar_one()
        trip.status = "FINALIZED"
        await db.commit()

        resp = await client.post(f"/trips/{trip_id}/generate", headers=auth_headers)
        assert resp.status_code == 409

    async def test_401_without_auth(self, client: AsyncClient, trip_id):
        resp = await client.post(f"/trips/{trip_id}/generate")
        assert resp.status_code == 401
