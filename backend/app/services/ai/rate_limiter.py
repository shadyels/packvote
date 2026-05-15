import asyncio
import time
from collections import deque
from dataclasses import dataclass

MAX_CONTEXT_TOKENS = 131_000
MAX_RPM = 1_000
MAX_TPM = 1_000_000
WINDOW_SECONDS = 60.0


class LocalRateLimitError(Exception):
    def __init__(self, kind: str, retry_after_seconds: float) -> None:
        self.kind = kind  # "rpm" | "tpm" | "context_length"
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Local rate limit hit ({kind}); retry after {retry_after_seconds:.1f}s"
        )


@dataclass
class Reservation:
    timestamp: float
    estimated_tokens: int


class GlobalRateLimiter:
    def __init__(self) -> None:
        self._requests: deque[float] = deque()
        self._tokens: deque[tuple[float, int]] = deque()
        self._lock = asyncio.Lock()

    def _evict(self, now: float) -> None:
        cutoff = now - WINDOW_SECONDS
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        while self._tokens and self._tokens[0][0] < cutoff:
            self._tokens.popleft()

    async def reserve(self, estimated_tokens: int) -> Reservation:
        if estimated_tokens > MAX_CONTEXT_TOKENS:
            raise LocalRateLimitError("context_length", 0.0)
        async with self._lock:
            now = time.monotonic()
            self._evict(now)
            if len(self._requests) >= MAX_RPM:
                retry = WINDOW_SECONDS - (now - self._requests[0])
                raise LocalRateLimitError("rpm", max(retry, 0.0))
            current_tokens = sum(n for _, n in self._tokens)
            if current_tokens + estimated_tokens > MAX_TPM:
                retry = WINDOW_SECONDS - (now - self._tokens[0][0])
                raise LocalRateLimitError("tpm", max(retry, 0.0))
            self._requests.append(now)
            self._tokens.append((now, estimated_tokens))
            return Reservation(timestamp=now, estimated_tokens=estimated_tokens)

    async def commit(self, reservation: Reservation, actual_tokens: int) -> None:
        """Replace the reservation's estimate with actual usage post-call."""
        async with self._lock:
            for i, (ts, _) in enumerate(self._tokens):
                if ts == reservation.timestamp:
                    self._tokens[i] = (ts, actual_tokens)
                    return


_limiter: GlobalRateLimiter | None = None


def get_limiter() -> GlobalRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = GlobalRateLimiter()
    return _limiter
