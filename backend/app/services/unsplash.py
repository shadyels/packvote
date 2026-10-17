import time

import httpx

from app.core.config import get_settings
from app.services.rate_limit import SlidingWindow

WINDOW_SECONDS = 3600.0
MAX_RPH = 50
MAX_COUNT = 10  # endpoint caps `count` at 10 (api/unsplash.py); fetch that once
_CACHE_TTL = 3600.0
_CACHE_MAX = 500

_limiter = SlidingWindow(MAX_RPH, WINDOW_SECONDS)
# ponytail: one entry per destination, capped at _CACHE_MAX with oldest-first
# eviction; swap for an LRU/TTL cache lib if hit-rate matters.
_cache: dict[str, tuple[float, list[str]]] = {}


async def fetch_destination_images(destination: str, count: int) -> list[str]:
    settings = get_settings()
    if not settings.UNSPLASH_ACCESS_KEY:
        return []

    key = destination.lower().strip()
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None:
        expires_at, urls = cached
        if now < expires_at:
            return urls[:count]

    if not _limiter.acquire():
        return []

    try:
        query = f"{destination} travel landscape"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": query,
                    "orientation": "landscape",
                    "per_page": MAX_COUNT,
                },
                headers={"Authorization": f"Client-ID {settings.UNSPLASH_ACCESS_KEY}"},
                timeout=10.0,
            )
        if not resp.is_success:
            return []

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return []

        urls = [
            r["urls"]["regular"] for r in results if r.get("urls", {}).get("regular")
        ]
        if not urls:
            return []

        if len(_cache) >= _CACHE_MAX:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (now + _CACHE_TTL, urls)
        return urls[:count]
    except Exception:
        return []
