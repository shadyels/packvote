"""Unit tests for EmailService (app/services/email/brevo.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email.brevo import EmailService

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def email_service() -> EmailService:
    return EmailService(
        api_key="test-brevo-key",
        frontend_url="https://packvote.test",
        from_email="noreply@packvote.test",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ok_response(status: int = 201) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    return resp


def _patch_httpx(status: int = 201):
    """Patch httpx.AsyncClient so no real HTTP calls are made."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=_make_ok_response(status))
    return patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# send_invitation
# ---------------------------------------------------------------------------


class TestSendInvitation:
    async def test_returns_true_on_201(self, email_service: EmailService) -> None:
        with _patch_httpx(201):
            result = await email_service.send_invitation(
                to_email="alice@example.com",
                participant_name="Alice",
                trip_title="Summer Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="tok-abc",
            )
        assert result is True

    async def test_returns_true_on_200(self, email_service: EmailService) -> None:
        with _patch_httpx(200):
            result = await email_service.send_invitation(
                to_email="alice@example.com",
                participant_name=None,
                trip_title="Trip",
                trip_code="ABCD1234",
                pin="0000",
                token="tok",
            )
        assert result is True

    async def test_returns_false_on_exception(self, email_service: EmailService) -> None:
        with patch(
            "app.services.email.brevo.httpx.AsyncClient", side_effect=RuntimeError("network error")
        ):
            result = await email_service.send_invitation(
                to_email="alice@example.com",
                participant_name="Alice",
                trip_title="Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="tok",
            )
        assert result is False

    async def test_subject_contains_trip_title(self, email_service: EmailService) -> None:
        captured: dict = {}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def capture_post(url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("json", {}))
            return _make_ok_response()

        mock_client.post = capture_post

        with patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client):
            await email_service.send_invitation(
                to_email="a@a.com",
                participant_name=None,
                trip_title="Summer Adventure",
                trip_code="TRIP1234",
                pin="5678",
                token="tok-xyz",
            )

        assert "Summer Adventure" in captured["subject"]

    async def test_body_contains_token_link_and_code_and_pin(
        self, email_service: EmailService
    ) -> None:
        captured: dict = {}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def capture_post(url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("json", {}))
            return _make_ok_response()

        mock_client.post = capture_post

        with patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client):
            await email_service.send_invitation(
                to_email="a@a.com",
                participant_name=None,
                trip_title="Trip",
                trip_code="TRIP1234",
                pin="5678",
                token="tok-xyz",
            )

        body: str = captured["textContent"]
        assert "tok-xyz" in body
        assert "TRIP1234" in body
        assert "5678" in body


# ---------------------------------------------------------------------------
# send_voting_notification
# ---------------------------------------------------------------------------


class TestSendVotingNotification:
    async def test_subject_contains_vote_now(self, email_service: EmailService) -> None:
        captured: dict = {}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def capture_post(url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("json", {}))
            return _make_ok_response()

        mock_client.post = capture_post

        with patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client):
            await email_service.send_voting_notification(
                to_email="a@a.com",
                participant_name="Alice",
                trip_title="Summer Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="tok",
            )

        assert "Vote now" in captured["subject"] or "vote" in captured["subject"].lower()

    async def test_body_contains_vote_link(self, email_service: EmailService) -> None:
        captured: dict = {}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def capture_post(url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("json", {}))
            return _make_ok_response()

        mock_client.post = capture_post

        with patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client):
            await email_service.send_voting_notification(
                to_email="a@a.com",
                participant_name=None,
                trip_title="Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="my-token",
            )

        assert "/vote" in captured["textContent"]
        assert "my-token" in captured["textContent"]


# ---------------------------------------------------------------------------
# send_new_iteration_notification
# ---------------------------------------------------------------------------


class TestSendNewIterationNotification:
    async def test_subject_contains_new_options(
        self, email_service: EmailService
    ) -> None:
        captured: dict = {}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def capture_post(url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("json", {}))
            return _make_ok_response()

        mock_client.post = capture_post

        with patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client):
            await email_service.send_new_iteration_notification(
                to_email="a@a.com",
                participant_name=None,
                trip_title="Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="tok",
            )

        assert "New options" in captured["subject"] or "new" in captured["subject"].lower()


# ---------------------------------------------------------------------------
# send_finalized_notification
# ---------------------------------------------------------------------------


class TestSendFinalizedNotification:
    async def test_subject_and_body_contain_destination(
        self, email_service: EmailService
    ) -> None:
        captured: dict = {}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def capture_post(url: str, **kwargs: object) -> MagicMock:
            captured.update(kwargs.get("json", {}))
            return _make_ok_response()

        mock_client.post = capture_post

        with patch("app.services.email.brevo.httpx.AsyncClient", return_value=mock_client):
            await email_service.send_finalized_notification(
                to_email="a@a.com",
                participant_name=None,
                trip_title="Our Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="tok",
                destination_name="Bali",
            )

        assert "Bali" in captured["subject"]
        assert "Bali" in captured["textContent"]

    async def test_returns_false_on_exception(self, email_service: EmailService) -> None:
        with patch(
            "app.services.email.brevo.httpx.AsyncClient", side_effect=Exception("api error")
        ):
            result = await email_service.send_finalized_notification(
                to_email="a@a.com",
                participant_name=None,
                trip_title="Trip",
                trip_code="ABCD1234",
                pin="1234",
                token="tok",
                destination_name="Bali",
            )
        assert result is False
