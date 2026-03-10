import re
import secrets

import pytest
from httpx import AsyncClient

from app.core.dependencies import get_email_service
from app.main import app

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
TRIPS_URL = "/trips/"


class MockEmailService:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_invitation(
        self,
        to_email: str,
        participant_name: str | None,
        trip_title: str,
        trip_code: str,
        pin: str,
        token: str,
    ) -> bool:
        self.sent.append({"to": to_email, "trip_code": trip_code})
        return True


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"user_{secrets.token_hex(4)}@test.com"
    await client.post(REGISTER_URL, json={"email": email, "password": "test1234"})
    resp = await client.post(LOGIN_URL, json={"email": email, "password": "test1234"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def mock_email():
    svc = MockEmailService()
    app.dependency_overrides[get_email_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_email_service, None)


_TRIP_PAYLOAD = {
    "title": "Summer Adventure",
    "participant_emails": ["alice@example.com", "bob@example.com"],
}


class TestCreateTrip:
    async def test_success_returns_201(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Summer Adventure"
        assert "id" in data
        assert "trip_code" in data
        assert "pin" in data
        assert "status" in data

    async def test_trip_code_is_8_char_uppercase_alphanum(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        trip_code = resp.json()["trip_code"]
        assert len(trip_code) == 8
        assert re.fullmatch(r"[A-Z0-9]{8}", trip_code)

    async def test_pin_is_4_digits(self, client: AsyncClient, auth_headers, mock_email):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        pin = resp.json()["pin"]
        assert len(pin) == 4
        assert re.fullmatch(r"\d{4}", pin)

    async def test_invitations_sent_per_participant(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        # Allow a moment for fire-and-forget gather
        import asyncio

        await asyncio.sleep(0)
        assert len(mock_email.sent) == 2
        sent_emails = {e["to"] for e in mock_email.sent}
        assert sent_emails == {"alice@example.com", "bob@example.com"}

    async def test_num_options_defaults_to_3(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["num_options"] == 3

    async def test_num_options_below_2_returns_422(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {**_TRIP_PAYLOAD, "num_options": 1}
        resp = await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_num_options_above_5_returns_422(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {**_TRIP_PAYLOAD, "num_options": 6}
        resp = await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_no_auth_returns_401(self, client: AsyncClient, mock_email):
        resp = await client.post(TRIPS_URL, json=_TRIP_PAYLOAD)
        assert resp.status_code == 401


class TestListTrips:
    async def test_empty_list(self, client: AsyncClient, auth_headers, mock_email):
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_only_callers_trips_returned(self, client: AsyncClient, mock_email):
        # Create two users, each creates a trip
        email_a = f"a_{secrets.token_hex(4)}@test.com"
        email_b = f"b_{secrets.token_hex(4)}@test.com"
        for email in (email_a, email_b):
            await client.post(
                REGISTER_URL, json={"email": email, "password": "test1234"}
            )

        async def login(email: str) -> dict:
            r = await client.post(
                LOGIN_URL, json={"email": email, "password": "test1234"}
            )
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        headers_a = await login(email_a)
        headers_b = await login(email_b)

        await client.post(
            TRIPS_URL, json={**_TRIP_PAYLOAD, "title": "Trip A"}, headers=headers_a
        )
        await client.post(
            TRIPS_URL, json={**_TRIP_PAYLOAD, "title": "Trip B"}, headers=headers_b
        )

        resp_a = await client.get(TRIPS_URL, headers=headers_a)
        assert resp_a.status_code == 200
        titles = [t["title"] for t in resp_a.json()]
        assert "Trip A" in titles
        assert "Trip B" not in titles

    async def test_participant_count_correct(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        payload = {
            **_TRIP_PAYLOAD,
            "participant_emails": ["p1@x.com", "p2@x.com", "p3@x.com"],
        }
        await client.post(TRIPS_URL, json=payload, headers=auth_headers)
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        trip = resp.json()[0]
        assert trip["participant_count"] == 3

    async def test_preferences_submitted_count(
        self, client: AsyncClient, auth_headers, mock_email
    ):
        await client.post(TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers)
        resp = await client.get(TRIPS_URL, headers=auth_headers)
        assert resp.status_code == 200
        # No preferences submitted yet
        assert resp.json()[0]["preferences_submitted_count"] == 0

    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(TRIPS_URL)
        assert resp.status_code == 401


class TestGetTrip:
    async def test_success(self, client: AsyncClient, auth_headers, mock_email):
        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=auth_headers
        )
        trip_id = create_resp.json()["id"]
        resp = await client.get(f"/trips/{trip_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == trip_id

    async def test_404_nonexistent(self, client: AsyncClient, auth_headers):
        resp = await client.get("/trips/999999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_403_when_not_creator(self, client: AsyncClient, mock_email):
        # User A creates trip
        email_a = f"a_{secrets.token_hex(4)}@test.com"
        email_b = f"b_{secrets.token_hex(4)}@test.com"
        for email in (email_a, email_b):
            await client.post(
                REGISTER_URL, json={"email": email, "password": "test1234"}
            )

        r_a = await client.post(
            LOGIN_URL, json={"email": email_a, "password": "test1234"}
        )
        headers_a = {"Authorization": f"Bearer {r_a.json()['access_token']}"}
        r_b = await client.post(
            LOGIN_URL, json={"email": email_b, "password": "test1234"}
        )
        headers_b = {"Authorization": f"Bearer {r_b.json()['access_token']}"}

        create_resp = await client.post(
            TRIPS_URL, json=_TRIP_PAYLOAD, headers=headers_a
        )
        trip_id = create_resp.json()["id"]

        resp = await client.get(f"/trips/{trip_id}", headers=headers_b)
        assert resp.status_code == 403

    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get("/trips/1")
        assert resp.status_code == 401
