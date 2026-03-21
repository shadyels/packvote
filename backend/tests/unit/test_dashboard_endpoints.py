"""Tests for dashboard-specific trip sub-resource endpoints.

Covers:
  GET /trips/{trip_id}/participants
  GET /trips/{trip_id}/itineraries
"""

import secrets

import pytest
from httpx import AsyncClient

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
TRIPS_URL = "/trips/"

_TRIP_PAYLOAD = {
    "title": "Dashboard Test Trip",
    "participant_emails": ["alice@example.com", "bob@example.com"],
}


@pytest.fixture
async def trip_id(client: AsyncClient, auth_headers, mock_email) -> int:
    resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


class TestGetTripParticipants:
    async def test_returns_all_participants(
        self, client: AsyncClient, auth_headers, trip_id, mock_email
    ):
        resp = await client.get(f"/trips/{trip_id}/participants", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        emails = {p["email"] for p in data}
        assert emails == {"alice@example.com", "bob@example.com"}

    async def test_participant_fields_present(
        self, client: AsyncClient, auth_headers, trip_id, mock_email
    ):
        resp = await client.get(f"/trips/{trip_id}/participants", headers=auth_headers)
        assert resp.status_code == 200
        p = resp.json()[0]
        assert "id" in p
        assert "trip_id" in p
        assert "email" in p
        assert "name" in p
        assert "preferences_submitted" in p
        assert "created_at" in p
        assert p["preferences_submitted"] is False

    async def test_403_when_not_creator(self, client: AsyncClient, mock_email, trip_id):
        other_email = f"other_{secrets.token_hex(4)}@test.com"
        await client.post(
            REGISTER_URL, json={"email": other_email, "password": "test1234"}
        )
        r = await client.post(
            LOGIN_URL, json={"email": other_email, "password": "test1234"}
        )
        other_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        resp = await client.get(f"/trips/{trip_id}/participants", headers=other_headers)
        assert resp.status_code == 403

    async def test_404_nonexistent_trip(self, client: AsyncClient, auth_headers):
        resp = await client.get("/trips/999999/participants", headers=auth_headers)
        assert resp.status_code == 404

    async def test_401_no_auth(self, client: AsyncClient, trip_id):
        resp = await client.get(f"/trips/{trip_id}/participants")
        assert resp.status_code == 401


class TestGetTripItineraries:
    async def test_empty_when_no_itineraries(
        self, client: AsyncClient, auth_headers, trip_id, mock_email
    ):
        resp = await client.get(f"/trips/{trip_id}/itineraries", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_403_when_not_creator(self, client: AsyncClient, mock_email, trip_id):
        other_email = f"other_{secrets.token_hex(4)}@test.com"
        await client.post(
            REGISTER_URL, json={"email": other_email, "password": "test1234"}
        )
        r = await client.post(
            LOGIN_URL, json={"email": other_email, "password": "test1234"}
        )
        other_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        resp = await client.get(f"/trips/{trip_id}/itineraries", headers=other_headers)
        assert resp.status_code == 403

    async def test_404_nonexistent_trip(self, client: AsyncClient, auth_headers):
        resp = await client.get("/trips/999999/itineraries", headers=auth_headers)
        assert resp.status_code == 404

    async def test_401_no_auth(self, client: AsyncClient, trip_id):
        resp = await client.get(f"/trips/{trip_id}/itineraries")
        assert resp.status_code == 401
