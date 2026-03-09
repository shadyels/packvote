import secrets

import pytest
from httpx import AsyncClient

from app.core.dependencies import get_email_service
from app.main import app

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
TRIPS_URL = "/trips/"
ACCESS_BY_CODE_URL = "/participants/access-by-code"


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
        self.sent.append({"to": to_email, "trip_code": trip_code, "token": token})
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


@pytest.fixture
async def created_trip(client: AsyncClient, auth_headers, mock_email):
    """Returns (trip_data, mock_email_service) after creating a trip."""
    resp = await client.post(
        TRIPS_URL,
        json={"title": "Test Trip", "participant_emails": ["guest@example.com"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    import asyncio
    await asyncio.sleep(0)
    return resp.json(), mock_email


class TestAccessByCode:
    async def test_success(self, client: AsyncClient, created_trip):
        trip, _ = created_trip
        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": trip["trip_code"], "pin": trip["pin"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["trip_id"] == trip["id"]

    async def test_wrong_pin_returns_401(self, client: AsyncClient, created_trip):
        trip, _ = created_trip
        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": trip["trip_code"], "pin": "0000"},
        )
        assert resp.status_code == 401

    async def test_bad_trip_code_returns_404(self, client: AsyncClient, created_trip):
        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": "XXXXXXXX", "pin": "1234"},
        )
        assert resp.status_code == 404


class TestGetParticipantByToken:
    async def test_success(self, client: AsyncClient, created_trip):
        trip, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        resp = await client.get(f"/participants/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trip_id"] == trip["id"]

    async def test_invalid_token_returns_404(self, client: AsyncClient, created_trip):
        resp = await client.get("/participants/totally-invalid-token-xyz")
        assert resp.status_code == 404


class TestSubmitPreferences:
    async def test_success_returns_201(self, client: AsyncClient, created_trip):
        trip, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        payload = {
            "budget_min": 500,
            "budget_max": 2000,
            "currency": "USD",
            "interests": "beaches, hiking",
            "activity_tags": ["outdoor", "food"],
        }
        resp = await client.post(f"/participants/{token}/preferences", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["budget_min"] == 500
        assert data["budget_max"] == 2000
        assert data["currency"] == "USD"
        assert data["interests"] == "beaches, hiking"
        assert "id" in data and "submitted_at" in data

    async def test_minimal_payload_accepted(self, client: AsyncClient, created_trip):
        _, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        resp = await client.post(f"/participants/{token}/preferences", json={})
        assert resp.status_code == 201

    async def test_sets_preferences_submitted_flag(self, client: AsyncClient, created_trip):
        trip, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        await client.post(f"/participants/{token}/preferences", json={})
        resp = await client.get(f"/participants/{token}")
        assert resp.json()["preferences_submitted"] is True

    async def test_resubmit_updates_existing(self, client: AsyncClient, created_trip):
        _, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        await client.post(f"/participants/{token}/preferences", json={"budget_max": 1000})
        resp = await client.post(f"/participants/{token}/preferences", json={"budget_max": 2500})
        assert resp.status_code == 201
        assert resp.json()["budget_max"] == 2500

    async def test_invalid_token_returns_404(self, client: AsyncClient, created_trip):
        resp = await client.post("/participants/bad-token-xyz/preferences", json={})
        assert resp.status_code == 404

    async def test_negative_budget_returns_422(self, client: AsyncClient, created_trip):
        _, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        resp = await client.post(
            f"/participants/{token}/preferences", json={"budget_min": -100}
        )
        assert resp.status_code == 422
