"""Integration tests for admin email resend endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "testpass123", "full_name": "Test User"},
    )
    resp = await client.post(
        "/auth/login", json={"email": email, "password": "testpass123"}
    )
    return resp.json()["access_token"]


async def _create_trip(
    client: AsyncClient, token: str, emails: list[str] | None = None
) -> dict:
    resp = await client.post(
        "/trips/",
        json={
            "title": "Test Trip",
            "num_options": 2,
            "participant_emails": emails or ["p1@example.com"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


class TestResendAll:
    async def test_sends_invitation_during_collecting(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        token = await _register_and_login(client, "creator1@example.com")
        trip = await _create_trip(client, token, ["p1@example.com", "p2@example.com"])

        mock_email.sent.clear()
        resp = await client.post(
            f"/admin/trips/{trip['id']}/resend-emails",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] >= 1
        assert all(e["type"] == "invitation" for e in mock_email.sent)

    async def test_returns_sent_and_failed_counts(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        token = await _register_and_login(client, "creator2@example.com")
        trip = await _create_trip(client, token, ["a@example.com", "b@example.com"])

        mock_email.sent.clear()
        resp = await client.post(
            f"/admin/trips/{trip['id']}/resend-emails",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "sent" in data
        assert "failed" in data

    async def test_requires_auth(self, client: AsyncClient, mock_email) -> None:
        resp = await client.post("/admin/trips/999/resend-emails")
        assert resp.status_code == 401

    async def test_forbidden_for_non_creator(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        creator_token = await _register_and_login(client, "creator3@example.com")
        other_token = await _register_and_login(client, "other3@example.com")
        trip = await _create_trip(client, creator_token)

        resp = await client.post(
            f"/admin/trips/{trip['id']}/resend-emails",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    async def test_trip_not_found(
        self, client: AsyncClient, mock_email, mock_session_factory
    ) -> None:
        token = await _register_and_login(client, "creator4@example.com")
        resp = await client.post(
            "/admin/trips/999999/resend-emails",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestResendOne:
    async def test_sends_to_single_participant(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        token = await _register_and_login(client, "creator5@example.com")
        trip = await _create_trip(client, token, ["single@example.com"])

        parts_resp = await client.get(
            f"/trips/{trip['id']}/participants",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert parts_resp.status_code == 200
        participants = parts_resp.json()
        assert len(participants) >= 1
        participant_id = participants[0]["id"]

        mock_email.sent.clear()
        resp = await client.post(
            f"/admin/trips/{trip['id']}/participants/{participant_id}/resend-email",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] == 1
        assert data["failed"] == 0
        assert len(mock_email.sent) == 1

    async def test_participant_not_found(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        token = await _register_and_login(client, "creator6@example.com")
        trip = await _create_trip(client, token)

        resp = await client.post(
            f"/admin/trips/{trip['id']}/participants/999999/resend-email",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_requires_auth(self, client: AsyncClient, mock_email) -> None:
        resp = await client.post("/admin/trips/1/participants/1/resend-email")
        assert resp.status_code == 401

    async def test_forbidden_for_non_creator(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        creator_token = await _register_and_login(client, "creator7@example.com")
        other_token = await _register_and_login(client, "other7@example.com")
        trip = await _create_trip(client, creator_token, ["p@example.com"])

        parts_resp = await client.get(
            f"/trips/{trip['id']}/participants",
            headers={"Authorization": f"Bearer {creator_token}"},
        )
        participant_id = parts_resp.json()[0]["id"]

        resp = await client.post(
            f"/admin/trips/{trip['id']}/participants/{participant_id}/resend-email",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403
