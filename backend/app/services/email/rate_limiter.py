import asyncio
import time
from collections import deque

WINDOW_SECONDS = 86400.0  # 24-hour sliding window
MAX_EPD = 300             # Brevo free tier: emails per day


class BrevoRateLimiter:
    def __init__(self) -> None:
        self._emails: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def try_consume(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - WINDOW_SECONDS
            while self._emails and self._emails[0] < cutoff:
                self._emails.popleft()
            if len(self._emails) >= MAX_EPD:
                return False
            self._emails.append(now)
            return True


_limiter: BrevoRateLimiter | None = None


def get_brevo_limiter() -> BrevoRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = BrevoRateLimiter()
    return _limiter
