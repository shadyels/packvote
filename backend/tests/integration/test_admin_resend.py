"""Integration tests for admin email resend endpoints."""

from httpx import AsyncClient

from tests.helpers import auth_headers, create_trip, register_and_login


class TestResendAll:
    async def test_sends_invitation_during_collecting(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        token = await register_and_login(client, "creator1@example.com")
        trip = await create_trip(client, token, ["p1@example.com", "p2@example.com"])

        mock_email.sent.clear()
        resp = await client.post(
            f"/admin/trips/{trip['id']}/resend-emails",
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] == len(mock_email.sent) >= 2
        assert data["failed"] == 0
        assert all(e["type"] == "invitation" for e in mock_email.sent)

    async def test_requires_auth(self, client: AsyncClient, mock_email) -> None:
        resp = await client.post("/admin/trips/999/resend-emails")
        assert resp.status_code == 401

    async def test_forbidden_for_non_creator(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        creator_token = await register_and_login(client, "creator3@example.com")
        other_token = await register_and_login(client, "other3@example.com")
        trip = await create_trip(client, creator_token)

        resp = await client.post(
            f"/admin/trips/{trip['id']}/resend-emails",
            headers=auth_headers(other_token),
        )
        assert resp.status_code == 403

    async def test_trip_not_found(
        self, client: AsyncClient, mock_email, mock_session_factory
    ) -> None:
        token = await register_and_login(client, "creator4@example.com")
        resp = await client.post(
            "/admin/trips/999999/resend-emails",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404


class TestResendOne:
    async def test_sends_to_single_participant(
        self,
        client: AsyncClient,
        mock_email,
        mock_session_factory,
    ) -> None:
        token = await register_and_login(client, "creator5@example.com")
        trip = await create_trip(client, token, ["single@example.com"])

        parts_resp = await client.get(
            f"/trips/{trip['id']}/participants",
            headers=auth_headers(token),
        )
        assert parts_resp.status_code == 200
        participants = parts_resp.json()
        assert len(participants) >= 1
        participant_id = participants[0]["id"]

        mock_email.sent.clear()
        resp = await client.post(
            f"/admin/trips/{trip['id']}/participants/{participant_id}/resend-email",
            headers=auth_headers(token),
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
        token = await register_and_login(client, "creator6@example.com")
        trip = await create_trip(client, token)

        resp = await client.post(
            f"/admin/trips/{trip['id']}/participants/999999/resend-email",
            headers=auth_headers(token),
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
        creator_token = await register_and_login(client, "creator7@example.com")
        other_token = await register_and_login(client, "other7@example.com")
        trip = await create_trip(client, creator_token, ["p@example.com"])

        parts_resp = await client.get(
            f"/trips/{trip['id']}/participants",
            headers=auth_headers(creator_token),
        )
        participant_id = parts_resp.json()[0]["id"]

        resp = await client.post(
            f"/admin/trips/{trip['id']}/participants/{participant_id}/resend-email",
            headers=auth_headers(other_token),
        )
        assert resp.status_code == 403
