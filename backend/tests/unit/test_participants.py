import secrets
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import get_email_service, get_session_factory
from app.main import app
from app.models.trip import Trip

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
TRIPS_URL = "/trips/"
ACCESS_BY_CODE_URL = "/participants/access-by-code"

GUEST_EMAIL = "guest@example.com"


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
def mock_session_factory(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app.dependency_overrides[get_session_factory] = lambda: factory
    yield factory
    app.dependency_overrides.pop(get_session_factory, None)


@pytest.fixture
async def created_trip(
    client: AsyncClient, auth_headers, mock_email, mock_session_factory
):
    """Returns (trip_data, mock_email_service) after creating a trip."""
    resp = await client.post(
        TRIPS_URL,
        json={"title": "Test Trip", "participant_emails": [GUEST_EMAIL]},
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
            json={
                "trip_code": trip["trip_code"],
                "pin": trip["pin"],
                "email": GUEST_EMAIL,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["participant"]["trip_id"] == trip["id"]
        assert "token" in data

    async def test_wrong_pin_returns_401(self, client: AsyncClient, created_trip):
        trip, _ = created_trip
        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": trip["trip_code"], "pin": "0000", "email": GUEST_EMAIL},
        )
        assert resp.status_code == 401

    async def test_bad_trip_code_returns_404(self, client: AsyncClient, created_trip):
        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={"trip_code": "XXXXXXXX", "pin": "1234", "email": GUEST_EMAIL},
        )
        assert resp.status_code == 404

    async def test_wrong_email_returns_404(self, client: AsyncClient, created_trip):
        trip, _ = created_trip
        resp = await client.post(
            ACCESS_BY_CODE_URL,
            json={
                "trip_code": trip["trip_code"],
                "pin": trip["pin"],
                "email": "nobody@example.com",
            },
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


class TestGetTripView:
    async def test_success(self, client: AsyncClient, created_trip):
        trip, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        resp = await client.get(f"/participants/{token}/trip-view")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trip"]["id"] == trip["id"]
        assert "participant" in data
        assert "participants" in data
        assert "itineraries" in data
        assert "has_voted" in data
        assert data["has_voted"] is False
        assert data["voting_results"] is None

    async def test_participant_brief_hides_email(self, client: AsyncClient, created_trip):
        _, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        resp = await client.get(f"/participants/{token}/trip-view")
        assert resp.status_code == 200
        for brief in resp.json()["participants"]:
            assert "email" not in brief

    async def test_invalid_token_returns_404(self, client: AsyncClient, created_trip):
        resp = await client.get("/participants/bad-token-xyz/trip-view")
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

    async def test_sets_preferences_submitted_flag(
        self, client: AsyncClient, created_trip
    ):
        trip, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        await client.post(f"/participants/{token}/preferences", json={})
        resp = await client.get(f"/participants/{token}")
        assert resp.json()["preferences_submitted"] is True

    async def test_resubmit_updates_existing(self, client: AsyncClient, created_trip):
        _, mock_email_svc = created_trip
        token = mock_email_svc.sent[0]["token"]
        await client.post(
            f"/participants/{token}/preferences", json={"budget_max": 1000}
        )
        resp = await client.post(
            f"/participants/{token}/preferences", json={"budget_max": 2500}
        )
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


class TestAutoTriggerGeneration:
    """When the last participant submits preferences, generation is auto-triggered."""

    @pytest.fixture
    async def two_participant_trip(self, client: AsyncClient, auth_headers, mock_email):
        """Create a trip with two participants and return (trip_data, tokens)."""
        resp = await client.post(
            TRIPS_URL,
            json={
                "title": "Auto Trigger Trip",
                "participant_emails": ["p1@test.com", "p2@test.com"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        import asyncio

        await asyncio.sleep(0)
        trip = resp.json()
        tokens = [e["token"] for e in mock_email.sent]
        return trip, tokens

    async def test_last_submission_triggers_generation(
        self,
        client: AsyncClient,
        two_participant_trip,
        db: AsyncSession,
        mock_session_factory,
    ):

        trip, tokens = two_participant_trip
        trip_id = trip["id"]

        mock_run = AsyncMock()
        with patch("app.services.generation.run_generation", mock_run):
            # First participant — should NOT trigger
            await client.post(f"/participants/{tokens[0]}/preferences", json={})
            mock_run.assert_not_called()

            # Second (last) participant — should trigger
            await client.post(f"/participants/{tokens[1]}/preferences", json={})

        mock_run.assert_called_once_with(trip_id, mock_session_factory)

    async def test_non_last_submission_does_not_trigger(
        self,
        client: AsyncClient,
        two_participant_trip,
        mock_session_factory,
    ):
        _, tokens = two_participant_trip

        mock_run = AsyncMock()
        with patch("app.services.generation.run_generation", mock_run):
            await client.post(f"/participants/{tokens[0]}/preferences", json={})

        mock_run.assert_not_called()

    async def test_trip_status_set_to_generating_on_auto_trigger(
        self,
        client: AsyncClient,
        two_participant_trip,
        db: AsyncSession,
        mock_session_factory,
    ):
        from sqlalchemy import select

        trip, tokens = two_participant_trip
        trip_id = trip["id"]

        with patch("app.services.generation.run_generation", AsyncMock()):
            await client.post(f"/participants/{tokens[0]}/preferences", json={})
            await client.post(f"/participants/{tokens[1]}/preferences", json={})

        db.expire_all()
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        updated_trip = result.scalar_one()
        assert updated_trip.status == "GENERATING"

    async def test_manual_trigger_blocks_auto_trigger(
        self,
        client: AsyncClient,
        auth_headers,
        two_participant_trip,
        db: AsyncSession,
        mock_session_factory,
    ):
        """If creator already triggered manually (status=GENERATING), auto-trigger is skipped."""
        from sqlalchemy import select

        trip, tokens = two_participant_trip
        trip_id = trip["id"]

        # Manually set status to GENERATING (simulating creator hit /generate first)
        result = await db.execute(select(Trip).where(Trip.id == trip_id))
        t = result.scalar_one()
        t.status = "GENERATING"
        await db.commit()

        mock_run = AsyncMock()
        with patch("app.services.generation.run_generation", mock_run):
            await client.post(f"/participants/{tokens[0]}/preferences", json={})
            await client.post(f"/participants/{tokens[1]}/preferences", json={})

        # run_generation should NOT have been called again
        mock_run.assert_not_called()
