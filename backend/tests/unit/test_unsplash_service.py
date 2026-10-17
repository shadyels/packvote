from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rate_limit import SlidingWindow
from app.services.unsplash import (
    _CACHE_MAX,
    MAX_COUNT,
    MAX_RPH,
    WINDOW_SECONDS,
    fetch_destination_images,
)

# --- fetch_destination_images ---


def _make_mock_response(urls: list[str], status: int = 200) -> MagicMock:
    results = [{"urls": {"regular": u}} for u in urls]
    resp = MagicMock()
    resp.is_success = status < 400
    resp.json.return_value = {"results": results}
    return resp


async def test_empty_key_returns_empty_no_rate_limit() -> None:
    limiter = SlidingWindow(MAX_RPH, WINDOW_SECONDS)
    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash._limiter", limiter),
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = ""
        result = await fetch_destination_images("Paris", 3)
    assert result == []
    # Rate limiter not consumed — still at 0
    assert limiter.allowed()
    assert len(limiter._events) == 0


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


async def test_over_rate_limit_returns_empty() -> None:
    import app.services.unsplash as svc_module

    # Install an exhausted limiter
    exhausted = SlidingWindow(MAX_RPH, WINDOW_SECONDS)
    for _ in range(MAX_RPH):
        exhausted.hit()

    original_limiter = svc_module._limiter
    svc_module._limiter = exhausted

    try:
        with patch("app.services.unsplash.get_settings") as mock_settings:
            mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
            result = await fetch_destination_images("RateLimitedCity", 1)
    finally:
        svc_module._limiter = original_limiter

    assert result == []


async def test_max_count_fetched_once_and_sliced() -> None:
    urls = [f"https://images.unsplash.com/{i}.jpg" for i in range(MAX_COUNT)]
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(return_value=_make_mock_response(urls))
    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        small = await fetch_destination_images("Lisbon", 2)
        large = await fetch_destination_images("lisbon ", MAX_COUNT)

    assert small == urls[:2]
    assert large == urls
    assert mock_instance.get.await_count == 1
    assert mock_instance.get.await_args.kwargs["params"]["per_page"] == MAX_COUNT


async def test_cache_is_capped() -> None:
    import app.services.unsplash as svc_module

    for i in range(_CACHE_MAX):
        svc_module._cache[f"d{i}"] = (1e12, ["u"])
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(return_value=_make_mock_response(["https://x/a.jpg"]))
    with (
        patch("app.services.unsplash.get_settings") as mock_settings,
        patch("app.services.unsplash.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_settings.return_value.UNSPLASH_ACCESS_KEY = "test-key"
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        await fetch_destination_images("brand-new", 1)

    assert len(svc_module._cache) == _CACHE_MAX
    assert "d0" not in svc_module._cache
