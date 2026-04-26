"""End-to-end integration smoke tests.

Exercises the real HTTP endpoints against an in-memory SQLite database
to ensure the router → service → ORM wiring is intact. These are
broad coverage checks — unit tests cover edge cases.
"""

import asyncio
import re

from httpx import AsyncClient

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
ME_URL = "/auth/me"
TRIPS_URL = "/trips/"
ACCESS_BY_CODE_URL = "/participants/access-by-code"


async def _register_and_login(client: AsyncClient, email: str) -> str:
    resp = await client.post(
        REGISTER_URL,
        json={"email": email, "password": "password123", "full_name": "Tester"},
    )
    assert resp.status_code == 201, resp.text
    resp = await client.post(
        LOGIN_URL, json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


class TestAuthFlow:
    async def test_register_login_me_roundtrip(self, client: AsyncClient):
        token = await _register_and_login(client, "creator@test.com")
        resp = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == "creator@test.com"

    async def test_me_requires_auth(self, client: AsyncClient):
        resp = await client.get(ME_URL)
        assert resp.status_code == 401

    async def test_login_with_wrong_password_fails(self, client: AsyncClient):
        await client.post(
            REGISTER_URL,
            json={"email": "x@test.com", "password": "correct-pass"},
        )
        resp = await client.post(
            LOGIN_URL, json={"email": "x@test.com", "password": "wrong-pass"}
        )
        assert resp.status_code == 401


class TestTripLifecycle:
    async def test_create_trip_produces_code_and_sends_invites(
        self, client: AsyncClient, mock_email
    ):
        token = await _register_and_login(client, "organizer@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            TRIPS_URL,
            json={
                "title": "Trip to Lisbon",
                "participant_emails": ["a@test.com", "b@test.com"],
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert re.fullmatch(r"[A-Z0-9]{8}", data["trip_code"])
        assert "pin" not in data

        # Allow fire-and-forget email gather to resolve
        await asyncio.sleep(0)
        invitations = [e for e in mock_email.sent if e["type"] == "invitation"]
        assert len(invitations) == 2
        assert {inv["to"] for inv in invitations} == {"a@test.com", "b@test.com"}

    async def test_participant_can_access_trip_with_code_and_pin(
        self, client: AsyncClient, mock_email
    ):
        token = await _register_and_login(client, "host@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        trip_resp = await client.post(
            TRIPS_URL,
            json={
                "title": "Ski Week",
                "participant_emails": ["friend@test.com"],
            },
            headers=headers,
        )
        trip_code = trip_resp.json()["trip_code"]

        await asyncio.sleep(0)
        assert mock_email.sent, "invitation email was not captured"
        invite = next(e for e in mock_email.sent if e["type"] == "invitation")
        pin = invite["pin"]
        assert re.fullmatch(r"\d{4}", pin)

        access_resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": trip_code, "pin": pin},
        )
        assert access_resp.status_code == 200, access_resp.text
        body = access_resp.json()
        assert "token" in body
        assert body["participant"]["email"] == "friend@test.com"

    async def test_access_with_bad_pin_is_rejected(
        self, client: AsyncClient, mock_email
    ):
        token = await _register_and_login(client, "host2@test.com")
        trip_resp = await client.post(
            TRIPS_URL,
            json={"title": "Bad Pin", "participant_emails": ["p@test.com"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        trip_code = trip_resp.json()["trip_code"]

        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": trip_code, "pin": "0000"},
        )
        assert resp.status_code in (401, 403, 404)

    async def test_creating_trip_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            TRIPS_URL,
            json={"title": "No Auth", "participant_emails": ["x@test.com"]},
        )
        assert resp.status_code == 401


INVITED_URL = "/trips/invited"


class TestInvitedTripsFlow:
    async def test_register_then_invited_trip_visible(
        self, client: AsyncClient, mock_email
    ):
        """B registers before A creates trip; create_trip links user_id immediately."""
        token_b = await _register_and_login(client, "b_first@test.com")
        token_a = await _register_and_login(client, "a_creator@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        resp = await client.post(
            TRIPS_URL,
            json={"title": "B was first", "participant_emails": ["b_first@test.com"]},
            headers=headers_a,
        )
        assert resp.status_code == 201, resp.text
        trip_id = resp.json()["id"]

        resp = await client.get(INVITED_URL, headers=headers_b)
        assert resp.status_code == 200
        payload = resp.json()
        ids = [t["id"] for t in payload]
        assert trip_id in ids
        invited = next(t for t in payload if t["id"] == trip_id)
        assert "participant_token" in invited
        assert isinstance(invited["participant_token"], str)
        assert len(invited["participant_token"]) > 0

    async def test_create_trip_then_register_backfills(
        self, client: AsyncClient, mock_email
    ):
        """A creates trip inviting B; B registers after; backfill links participant."""
        token_a = await _register_and_login(client, "a_early@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}

        resp = await client.post(
            TRIPS_URL,
            json={"title": "B joins late", "participant_emails": ["b_late@test.com"]},
            headers=headers_a,
        )
        assert resp.status_code == 201, resp.text
        trip_id = resp.json()["id"]

        # B registers after trip creation
        token_b = await _register_and_login(client, "b_late@test.com")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        resp = await client.get(INVITED_URL, headers=headers_b)
        assert resp.status_code == 200
        payload = resp.json()
        ids = [t["id"] for t in payload]
        assert trip_id in ids
        invited = next(t for t in payload if t["id"] == trip_id)
        assert "participant_token" in invited
        assert isinstance(invited["participant_token"], str)
        assert len(invited["participant_token"]) > 0

    async def test_get_trips_excludes_invited(self, client: AsyncClient, mock_email):
        """GET /trips/ for invitee must not include trips they were only invited to."""
        token_a = await _register_and_login(client, "a_host@test.com")
        token_b = await _register_and_login(client, "b_guest@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        resp = await client.post(
            TRIPS_URL,
            json={"title": "A hosts B", "participant_emails": ["b_guest@test.com"]},
            headers=headers_a,
        )
        assert resp.status_code == 201, resp.text

        resp = await client.get(TRIPS_URL, headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []
