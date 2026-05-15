import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.unsplash import (
    MAX_RPH,
    WINDOW_SECONDS,
    UnsplashRateLimiter,
    fetch_destination_images,
)

# --- Rate limiter ---


@pytest.mark.asyncio
async def test_rate_limiter_45_succeed() -> None:
    limiter = UnsplashRateLimiter()
    results = [await limiter.try_consume() for _ in range(MAX_RPH)]
    assert all(results)


@pytest.mark.asyncio
async def test_rate_limiter_46th_fails() -> None:
    limiter = UnsplashRateLimiter()
    for _ in range(MAX_RPH):
        await limiter.try_consume()
    assert not await limiter.try_consume()


@pytest.mark.asyncio
async def test_rate_limiter_evicts_old_entries() -> None:
    limiter = UnsplashRateLimiter()
    base_time = 1000.0

    with patch("app.services.unsplash.time.monotonic", return_value=base_time):
        for _ in range(MAX_RPH):
            await limiter.try_consume()
        assert not await limiter.try_consume()

    # Past the window — all entries evicted, new slots available
    with patch(
        "app.services.unsplash.time.monotonic",
        return_value=base_time + WINDOW_SECONDS + 1.0,
    ):
        assert await limiter.try_consume()


@pytest.mark.asyncio
async def test_concurrent_consumes_exactly_45_succeed() -> None:
    limiter = UnsplashRateLimiter()
    results = await asyncio.gather(
        *[limiter.try_consume() for _ in range(MAX_RPH + 10)]
    )
    assert sum(results) == MAX_RPH
    assert results.count(False) == 10


# --- fetch_destination_images ---


def _make_mock_response(urls: list[str], status: int = 200) -> MagicMock:
    results = [{"urls": {"regular": u}} for u in urls]
    resp = MagicMock()
    resp.is_success = status < 400
    resp.json.return_value = {"results": results}
    return resp


@pytest.mark.asyncio
async def test_empty_key_returns_empty_no_rate_limit() -> None:
    limiter = UnsplashRateLimiter()
    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.get_unsplash_limiter", return_value=limiter),
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = ""
        result = await fetch_destination_images("Paris", 3)
    assert result == []
    # Rate limiter not consumed — still at 0
    assert len(limiter._requests) == 0


@pytest.mark.asyncio
async def test_fetch_returns_image_urls() -> None:
    mock_resp = _make_mock_response(
        ["https://images.unsplash.com/a.jpg", "https://images.unsplash.com/b.jpg"]
    )
    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_destination_images("Tokyo", 2)

    assert result == [
        "https://images.unsplash.com/a.jpg",
        "https://images.unsplash.com/b.jpg",
    ]


@pytest.mark.asyncio
async def test_cache_prevents_second_fetch() -> None:
    import app.services.unsplash as svc_module

    # Clear module-level cache
    svc_module._cache.clear()

    mock_resp = _make_mock_response(["https://images.unsplash.com/cached.jpg"])
    call_count = 0

    async def fake_get(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal call_count
        call_count += 1
        return mock_resp

    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
        mock_instance = AsyncMock()
        mock_instance.get = fake_get
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        dest = "CachedCity_unique"
        await fetch_destination_images(dest, 1)
        await fetch_destination_images(dest, 1)

    assert call_count == 1


@pytest.mark.asyncio
async def test_unsplash_4xx_returns_empty() -> None:
    mock_resp = MagicMock()
    mock_resp.is_success = False

    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_destination_images("Nowhere", 1)

    assert result == []


@pytest.mark.asyncio
async def test_over_rate_limit_returns_empty() -> None:
    import app.services.unsplash as svc_module

    # Install an exhausted limiter
    exhausted = UnsplashRateLimiter()
    for _ in range(MAX_RPH):
        await exhausted.try_consume()

    original_limiter = svc_module._limiter
    svc_module._limiter = exhausted

    try:
        with patch("app.services.unsplash.get_settings") as mock_settings:
            mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
            result = await fetch_destination_images("RateLimitedCity", 1)
    finally:
        svc_module._limiter = original_limiter

    assert result == []
