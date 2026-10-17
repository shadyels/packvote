"""Integration tests for POST /trips/{id}/generate endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import Trip
from app.services.ai.service import AIService
from tests.helpers import auth_headers as auth_headers_for
from tests.helpers import register_and_login


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

    async def test_generate_runs_background_task_to_voting(
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
        # ASGITransport runs the background task before returning, so the mocked
        # generation has already completed: GENERATING -> VOTING.
        assert trip.status == "VOTING"

    async def test_404_for_nonexistent_trip(self, client: AsyncClient, auth_headers):
        resp = await client.post("/trips/99999/generate", headers=auth_headers)
        assert resp.status_code == 404

    async def test_403_for_non_owner(
        self, client: AsyncClient, trip_id, mock_email, mock_session_factory
    ):
        other_headers = auth_headers_for(
            await register_and_login(client, "other@test.com")
        )

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
