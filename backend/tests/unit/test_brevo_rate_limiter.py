"""Unit tests for BrevoRateLimiter."""
import asyncio
from unittest.mock import patch

import pytest

from app.services.email.rate_limiter import (
    MAX_EPD,
    WINDOW_SECONDS,
    BrevoRateLimiter,
)


# Deferred imports for integration tests (to allow unit-only runs)
import app.services.email.rate_limiter as _rl_module


@pytest.mark.asyncio
async def test_300_emails_all_accepted() -> None:
    limiter = BrevoRateLimiter()
    results = [await limiter.try_consume() for _ in range(MAX_EPD)]
    assert all(results)


@pytest.mark.asyncio
async def test_301st_email_rejected() -> None:
    limiter = BrevoRateLimiter()
    for _ in range(MAX_EPD):
        await limiter.try_consume()
    assert not await limiter.try_consume()


@pytest.mark.asyncio
async def test_sliding_window_evicts_old_entries() -> None:
    limiter = BrevoRateLimiter()
    base_time = 1_000_000.0

    with patch(
        "app.services.email.rate_limiter.time.monotonic", return_value=base_time
    ):
        for _ in range(MAX_EPD):
            await limiter.try_consume()
        assert not await limiter.try_consume()  # full at base_time

    # Past the 24-hour window — all entries evicted
    with patch(
        "app.services.email.rate_limiter.time.monotonic",
        return_value=base_time + WINDOW_SECONDS + 1.0,
    ):
        assert await limiter.try_consume()


@pytest.mark.asyncio
async def test_sliding_window_not_reset_before_expiry() -> None:
    limiter = BrevoRateLimiter()
    base_time = 1_000_000.0

    with patch(
        "app.services.email.rate_limiter.time.monotonic", return_value=base_time
    ):
        for _ in range(MAX_EPD):
            await limiter.try_consume()

    # One second before expiry — entries must still block
    with patch(
        "app.services.email.rate_limiter.time.monotonic",
        return_value=base_time + WINDOW_SECONDS - 1.0,
    ):
        assert not await limiter.try_consume()


@pytest.mark.asyncio
async def test_concurrent_consumes_exactly_300_succeed() -> None:
    limiter = BrevoRateLimiter()
    results = await asyncio.gather(
        *[limiter.try_consume() for _ in range(MAX_EPD + 20)]
    )
    assert sum(results) == MAX_EPD
    assert results.count(False) == 20


# ---------------------------------------------------------------------------
# Integration: _send() honours the rate limiter
# ---------------------------------------------------------------------------
from app.services.email.brevo import EmailService


@pytest.fixture
def email_svc() -> EmailService:
    return EmailService(
        api_key="test-key",
        frontend_url="https://packvote.test",
        from_email="noreply@packvote.test",
    )


@pytest.mark.asyncio
async def test_send_returns_false_when_limiter_exhausted(
    email_svc: EmailService,
) -> None:
    exhausted = BrevoRateLimiter()
    for _ in range(MAX_EPD):
        await exhausted.try_consume()

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


@pytest.mark.asyncio
async def test_send_logs_warning_when_rate_limited(
    email_svc: EmailService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    exhausted = BrevoRateLimiter()
    for _ in range(MAX_EPD):
        await exhausted.try_consume()

    original = _rl_module._limiter
    _rl_module._limiter = exhausted
    try:
        with caplog.at_level(logging.WARNING, logger="app.services.email.brevo"):
            await email_svc._send("x@x.com", "s", "b")
    finally:
        _rl_module._limiter = original

    assert any("rate limit" in rec.message.lower() for rec in caplog.records)


@pytest.mark.asyncio
async def test_send_succeeds_when_limiter_allows(email_svc: EmailService) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch as _patch

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    fresh_limiter = BrevoRateLimiter()
    original = _rl_module._limiter
    _rl_module._limiter = fresh_limiter
    try:
        with _patch(
            "app.services.email.brevo.httpx.AsyncClient", return_value=mock_client
        ):
            result = await email_svc._send("ok@example.com", "Hello", "World")
    finally:
        _rl_module._limiter = original

    assert result is True
