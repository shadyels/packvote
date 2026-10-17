import asyncio
from unittest.mock import patch

import pytest

from app.services.ai.rate_limiter import (
    MAX_CONTEXT_TOKENS,
    MAX_RPD,
    MAX_RPM,
    MAX_TPH,
    MAX_TPM,
    WINDOW_1M,
    GlobalRateLimiter,
    LocalRateLimitError,
)


async def test_fresh_limiter_accepts_small_request() -> None:
    limiter = GlobalRateLimiter()
    reservation = await limiter.reserve(1000)
    assert reservation.tokens == 1000
    assert reservation.timestamp > 0


async def test_rpm_gate_1000th_accepted_1001st_rejected() -> None:
    limiter = GlobalRateLimiter()
    for _ in range(MAX_RPM):
        await limiter.reserve(1)
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(1)
    assert exc_info.value.kind == "rpm"
    assert exc_info.value.retry_after_seconds <= WINDOW_1M
    assert exc_info.value.retry_after_seconds >= 0.0


async def test_tpm_gate_rejects_when_exceeded() -> None:
    limiter = GlobalRateLimiter()
    # Fill the TPM bucket in MAX_RPM-1 chunks so the RPM gate never fires first.
    # Sized from the constants so re-tuning for a new provider can't stale this.
    chunk = MAX_TPM // (MAX_RPM - 1)
    assert chunk <= MAX_CONTEXT_TOKENS
    for _ in range(MAX_RPM - 1):
        await limiter.reserve(chunk)
    used = chunk * (MAX_RPM - 1)
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(MAX_TPM - used + 1)
    assert exc_info.value.kind == "tpm"
    assert exc_info.value.retry_after_seconds >= 0.0


async def test_context_length_rejects_oversized_prompt() -> None:
    limiter = GlobalRateLimiter()
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(MAX_CONTEXT_TOKENS + 1)
    assert exc_info.value.kind == "context_length"
    assert exc_info.value.retry_after_seconds == 0.0


async def test_context_length_rejected_before_lock() -> None:
    # Confirm context_length check is pre-lock: limiter state should be unchanged
    limiter = GlobalRateLimiter()
    with pytest.raises(LocalRateLimitError):
        await limiter.reserve(MAX_CONTEXT_TOKENS + 1)
    # Should still accept a valid request after the oversized rejection
    reservation = await limiter.reserve(1000)
    assert reservation.tokens == 1000


async def test_commit_lowers_estimate_frees_token_room() -> None:
    limiter = GlobalRateLimiter()
    # Reserve 3/4 of the TPM budget across three optimistic estimates.
    chunk = MAX_TPM // 4
    first = await limiter.reserve(chunk)
    for _ in range(2):
        await limiter.reserve(chunk)
    # One more token past the remaining quarter must be refused.
    overflow = MAX_TPM - 3 * chunk + 1
    assert overflow <= MAX_CONTEXT_TOKENS
    with pytest.raises(LocalRateLimitError) as exc_info:
        await limiter.reserve(overflow)
    assert exc_info.value.kind == "tpm"
    # Commit the first reservation with a much lower actual — frees its room.
    limiter.commit(first, 1_000)
    r2 = await limiter.reserve(overflow)
    assert r2.tokens == overflow


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
    advanced_time = base_time + WINDOW_1M + 1.0
    with patch(
        "app.services.ai.rate_limiter.time.monotonic", return_value=advanced_time
    ):
        for _ in range(MAX_RPM):
            await limiter.reserve(1)
        # 1001st in new window should fail
        with pytest.raises(LocalRateLimitError) as exc_info:
            await limiter.reserve(1)
        assert exc_info.value.kind == "rpm"


async def test_daily_request_limit() -> None:
    limiter = GlobalRateLimiter()
    base = 1000.0
    for i in range(MAX_RPD):
        with patch(
            "app.services.ai.rate_limiter.time.monotonic", return_value=base + i * 34
        ):
            await limiter.reserve(100)
    last_ts = base + MAX_RPD * 34
    with patch("app.services.ai.rate_limiter.time.monotonic", return_value=last_ts):
        with pytest.raises(LocalRateLimitError) as exc_info:
            await limiter.reserve(100)
        assert exc_info.value.kind == "rpd"


async def test_hourly_token_limit() -> None:
    limiter = GlobalRateLimiter()
    base = 1000.0
    # Space reservations 61s apart so each falls out of the 1-minute window and
    # only the hourly total accumulates.
    chunk = min(MAX_CONTEXT_TOKENS, MAX_TPM)
    n = MAX_TPH // chunk
    assert n * 61 < 3_600, "fill must complete inside the 1-hour window"
    for i in range(n):
        with patch(
            "app.services.ai.rate_limiter.time.monotonic", return_value=base + i * 61
        ):
            await limiter.reserve(chunk)
    overflow = MAX_TPH - n * chunk + 1
    with patch(
        "app.services.ai.rate_limiter.time.monotonic", return_value=base + n * 61
    ):
        with pytest.raises(LocalRateLimitError) as exc_info:
            await limiter.reserve(overflow)
        assert exc_info.value.kind == "tph"
