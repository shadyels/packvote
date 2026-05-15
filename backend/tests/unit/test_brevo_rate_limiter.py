"""Unit tests for BrevoRateLimiter."""
import asyncio
from unittest.mock import patch

import pytest

from app.services.email.rate_limiter import (
    MAX_EPD,
    WINDOW_SECONDS,
    BrevoRateLimiter,
)


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
