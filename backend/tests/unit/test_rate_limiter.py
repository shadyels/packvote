import asyncio
from unittest.mock import patch

import pytest

from app.services.ai.rate_limiter import (
    MAX_CONTEXT_TOKENS,
    MAX_RPM,
    WINDOW_SECONDS,
    GlobalRateLimiter,
    LocalRateLimitError,
)


@pytest.mark.asyncio
async def test_fresh_limiter_accepts_small_request() -> None:
    limiter = GlobalRateLimiter()
    reservation = await limiter.reserve(1000)
    assert reservation.estimated_tokens == 1000
    assert reservation.timestamp > 0


@pytest.mark.asyncio
async def test_rpm_gate_1000th_accepted_1001st_rejected() -> None:
    limiter = GlobalRateLimiter()
    for _ in range(MAX_RPM):
        await limiter.reserve(1)
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(1)
    assert exc_info.value.kind == "rpm"
    assert exc_info.value.retry_after_seconds <= WINDOW_SECONDS
    assert exc_info.value.retry_after_seconds >= 0.0


@pytest.mark.asyncio
async def test_tpm_gate_rejects_when_exceeded() -> None:
    limiter = GlobalRateLimiter()
    # Fill TPM bucket using 10 × 100_000 = MAX_TPM (each ≤ MAX_CONTEXT_TOKENS)
    for _ in range(10):
        await limiter.reserve(100_000)
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(1)
    assert exc_info.value.kind == "tpm"
    assert exc_info.value.retry_after_seconds >= 0.0


@pytest.mark.asyncio
async def test_context_length_rejects_oversized_prompt() -> None:
    limiter = GlobalRateLimiter()
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(MAX_CONTEXT_TOKENS + 1)
    assert exc_info.value.kind == "context_length"
    assert exc_info.value.retry_after_seconds == 0.0


@pytest.mark.asyncio
async def test_context_length_rejected_before_lock() -> None:
    # Confirm context_length check is pre-lock: limiter state should be unchanged
    limiter = GlobalRateLimiter()
    with pytest.raises(LocalRateLimitError):
        await limiter.reserve(MAX_CONTEXT_TOKENS + 1)
    # Should still accept a valid request after the oversized rejection
    reservation = await limiter.reserve(1000)
    assert reservation.estimated_tokens == 1000


@pytest.mark.asyncio
async def test_commit_lowers_estimate_frees_token_room() -> None:
    limiter = GlobalRateLimiter()
    # Fill bucket: 9 × 100_000 = 900_000 tokens reserved
    first = await limiter.reserve(100_000)
    for _ in range(8):
        await limiter.reserve(100_000)
    # 110_000 would exceed TPM (900_000 + 110_000 = 1_010_000 > 1_000_000)
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(110_000)
    assert exc_info.value.kind == "tpm"
    # Commit first reservation with low actual — frees 99_000 tokens
    await limiter.commit(first, 1_000)
    # Now 110_000 fits: (900_000 - 99_000) + 110_000 = 911_000 < 1_000_000
    r2 = await limiter.reserve(110_000)
    assert r2.estimated_tokens == 110_000


@pytest.mark.asyncio
async def test_concurrent_reservations_exactly_1000_succeed() -> None:
    limiter = GlobalRateLimiter()
    results = await asyncio.gather(
        *[limiter.reserve(1) for _ in range(MAX_RPM + 100)],
        return_exceptions=True,
    )
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, LocalRateLimitError)]
    other_errors = [
        r
        for r in results
        if isinstance(r, Exception) and not isinstance(r, LocalRateLimitError)
    ]
    assert len(other_errors) == 0
    assert len(successes) == MAX_RPM
    assert len(failures) == 100
    assert all(e.kind == "rpm" for e in failures)


@pytest.mark.asyncio
async def test_sliding_window_resets_after_60_seconds() -> None:
    limiter = GlobalRateLimiter()
    base_time = 1000.0

    with patch("app.services.ai.rate_limiter.time.monotonic", return_value=base_time):
        for _ in range(MAX_RPM):
            await limiter.reserve(1)

    # Still within window — should be rejected
    with patch(
        "app.services.ai.rate_limiter.time.monotonic", return_value=base_time + 59.0
    ):
        with pytest.raises(LocalRateLimitError) as exc_info:
            await limiter.reserve(1)
        assert exc_info.value.kind == "rpm"

    # Past window — all old entries evicted, 1000 new slots available
    advanced_time = base_time + WINDOW_SECONDS + 1.0
    with patch(
        "app.services.ai.rate_limiter.time.monotonic", return_value=advanced_time
    ):
        for _ in range(MAX_RPM):
            await limiter.reserve(1)
        # 1001st in new window should fail
        with pytest.raises(LocalRateLimitError) as exc_info:
            await limiter.reserve(1)
        assert exc_info.value.kind == "rpm"
