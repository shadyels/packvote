"""Unit tests: EmailService._send honours the Brevo rate limiter."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.email.brevo as _rl_module
from app.services.email.brevo import MAX_EPD, EmailService
from app.services.rate_limit import SlidingWindow

# ---------------------------------------------------------------------------
# _send() honours the rate limiter
# ---------------------------------------------------------------------------


@pytest.fixture
def email_svc() -> EmailService:
    return EmailService(
        api_key="test-key",
        frontend_url="https://packvote.test",
        from_email="noreply@packvote.test",
    )


async def test_send_returns_false_when_limiter_exhausted(
    email_svc: EmailService,
) -> None:
    exhausted = SlidingWindow(MAX_EPD, 86400)
    for _ in range(MAX_EPD):
        exhausted.hit()

    original = _rl_module._limiter
    _rl_module._limiter = exhausted
    try:
        result = await email_svc._send(
            to_email="victim@example.com",
            subject="Test",
            body="Body",
        )
    finally:
        _rl_module._limiter = original

    assert result is False


async def test_send_logs_warning_when_rate_limited(
    email_svc: EmailService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    exhausted = SlidingWindow(MAX_EPD, 86400)
    for _ in range(MAX_EPD):
        exhausted.hit()

    original = _rl_module._limiter
    _rl_module._limiter = exhausted
    try:
        with caplog.at_level(logging.WARNING, logger="app.services.email.brevo"):
            await email_svc._send("x@x.com", "s", "b")
    finally:
        _rl_module._limiter = original

    assert any("rate limit" in rec.message.lower() for rec in caplog.records)


async def test_send_succeeds_when_limiter_allows(email_svc: EmailService) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    fresh_limiter = SlidingWindow(MAX_EPD, 86400)
    original = _rl_module._limiter
    _rl_module._limiter = fresh_limiter
    try:
        with patch(
            "app.services.email.brevo.httpx.AsyncClient", return_value=mock_client
        ):
            result = await email_svc._send("ok@example.com", "Hello", "World")
    finally:
        _rl_module._limiter = original

    assert result is True
