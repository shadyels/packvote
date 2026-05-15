import asyncio
import time
from collections import deque

import httpx

from app.core.config import get_settings

WINDOW_SECONDS = 3600.0
MAX_RPH = 45
_CACHE_TTL = 3600.0

_cache: dict[str, tuple[float, list[str]]] = {}


class UnsplashRateLimiter:
    def __init__(self) -> None:
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def try_consume(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - WINDOW_SECONDS
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            if len(self._requests) >= MAX_RPH:
                return False
            self._requests.append(now)
            return True


_limiter: UnsplashRateLimiter | None = None


def get_unsplash_limiter() -> UnsplashRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = UnsplashRateLimiter()
    return _limiter


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

    limiter = get_unsplash_limiter()
    if not await limiter.try_consume():
        return []

    try:
        query = f"{destination} travel landscape"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "orientation": "landscape", "per_page": count},
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

        _cache[key] = (now + _CACHE_TTL, urls)
        return urls
    except Exception:
        return []
