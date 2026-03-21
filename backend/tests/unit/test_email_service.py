"""Unit tests for EmailService (app/services/email/sendgrid.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.email.sendgrid import EmailService


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def email_service() -> EmailService:
    return EmailService(
        api_key="test-sg-key",
        frontend_url="https://packvote.test",
        from_email="noreply@packvote.test",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ok_response(status: int = 202) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    return resp


def _patched_sendgrid(status: int = 202):
    """Context manager pair: patches Mail (captures kwargs) + anyio + SendGridAPIClient."""
    return status


# ---------------------------------------------------------------------------
# send_invitation
# ---------------------------------------------------------------------------


class TestSendInvitation:
    async def test_returns_true_on_202(self, email_service: EmailService) -> None:
        with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = _make_ok_response(202)
            with patch("app.services.email.sendgrid.SendGridAPIClient"):
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
        with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = _make_ok_response(200)
            with patch("app.services.email.sendgrid.SendGridAPIClient"):
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
        with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = RuntimeError("network error")
            with patch("app.services.email.sendgrid.SendGridAPIClient"):
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

        def capture_mail(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch("app.services.email.sendgrid.Mail", side_effect=capture_mail):
            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = _make_ok_response()
                with patch("app.services.email.sendgrid.SendGridAPIClient"):
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

        def capture_mail(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch("app.services.email.sendgrid.Mail", side_effect=capture_mail):
            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = _make_ok_response()
                with patch("app.services.email.sendgrid.SendGridAPIClient"):
                    await email_service.send_invitation(
                        to_email="a@a.com",
                        participant_name=None,
                        trip_title="Trip",
                        trip_code="TRIP1234",
                        pin="5678",
                        token="tok-xyz",
                    )

        body: str = captured["plain_text_content"]
        assert "tok-xyz" in body
        assert "TRIP1234" in body
        assert "5678" in body


# ---------------------------------------------------------------------------
# send_voting_notification
# ---------------------------------------------------------------------------


class TestSendVotingNotification:
    async def test_subject_contains_vote_now(self, email_service: EmailService) -> None:
        captured: dict = {}

        def capture_mail(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch("app.services.email.sendgrid.Mail", side_effect=capture_mail):
            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = _make_ok_response()
                with patch("app.services.email.sendgrid.SendGridAPIClient"):
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

        def capture_mail(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch("app.services.email.sendgrid.Mail", side_effect=capture_mail):
            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = _make_ok_response()
                with patch("app.services.email.sendgrid.SendGridAPIClient"):
                    await email_service.send_voting_notification(
                        to_email="a@a.com",
                        participant_name=None,
                        trip_title="Trip",
                        trip_code="ABCD1234",
                        pin="1234",
                        token="my-token",
                    )

        assert "/vote" in captured["plain_text_content"]
        assert "my-token" in captured["plain_text_content"]


# ---------------------------------------------------------------------------
# send_new_iteration_notification
# ---------------------------------------------------------------------------


class TestSendNewIterationNotification:
    async def test_subject_contains_new_options(
        self, email_service: EmailService
    ) -> None:
        captured: dict = {}

        def capture_mail(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch("app.services.email.sendgrid.Mail", side_effect=capture_mail):
            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = _make_ok_response()
                with patch("app.services.email.sendgrid.SendGridAPIClient"):
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

        def capture_mail(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch("app.services.email.sendgrid.Mail", side_effect=capture_mail):
            with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
                mock_run.return_value = _make_ok_response()
                with patch("app.services.email.sendgrid.SendGridAPIClient"):
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
        assert "Bali" in captured["plain_text_content"]

    async def test_returns_false_on_exception(self, email_service: EmailService) -> None:
        with patch("anyio.to_thread.run_sync", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("api error")
            with patch("app.services.email.sendgrid.SendGridAPIClient"):
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
