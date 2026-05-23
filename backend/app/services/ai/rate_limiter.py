import asyncio
import time
from collections import deque
from dataclasses import dataclass

MAX_CONTEXT_TOKENS = 65_536
MAX_RPM, MAX_RPH, MAX_RPD = 5, 250, 2_400
MAX_TPM, MAX_TPH, MAX_TPD = 30_000, 1_000_000, 1_000_000
WINDOW_1M = 60.0
WINDOW_1H = 3_600.0
WINDOW_24H = 86_400.0


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
        cutoff = now - WINDOW_24H
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

            rpm = sum(1 for t in self._requests if t >= now - WINDOW_1M)
            rph = sum(1 for t in self._requests if t >= now - WINDOW_1H)
            rpd = len(self._requests)

            if rpm >= MAX_RPM:
                oldest = next(t for t in self._requests if t >= now - WINDOW_1M)
                raise LocalRateLimitError("rpm", WINDOW_1M - (now - oldest))
            if rph >= MAX_RPH:
                oldest = next(t for t in self._requests if t >= now - WINDOW_1H)
                raise LocalRateLimitError("rph", WINDOW_1H - (now - oldest))
            if rpd >= MAX_RPD:
                raise LocalRateLimitError("rpd", WINDOW_24H - (now - self._requests[0]))

            tpm = sum(n for ts, n in self._tokens if ts >= now - WINDOW_1M)
            tph = sum(n for ts, n in self._tokens if ts >= now - WINDOW_1H)
            tpd = sum(n for ts, n in self._tokens)

            if tpm + estimated_tokens > MAX_TPM:
                oldest = next(ts for ts, _ in self._tokens if ts >= now - WINDOW_1M)
                raise LocalRateLimitError("tpm", WINDOW_1M - (now - oldest))
            if tph + estimated_tokens > MAX_TPH:
                oldest = next(ts for ts, _ in self._tokens if ts >= now - WINDOW_1H)
                raise LocalRateLimitError("tph", WINDOW_1H - (now - oldest))
            if tpd + estimated_tokens > MAX_TPD:
                raise LocalRateLimitError(
                    "tpd", WINDOW_24H - (now - self._tokens[0][0])
                )

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
