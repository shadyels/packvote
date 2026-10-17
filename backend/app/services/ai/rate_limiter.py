import asyncio
import time
from collections import deque
from dataclasses import dataclass

# Calibrated against Google Gemini's free tier (~10 RPM / 250K TPM / ~1.5K RPD),
# deliberately set under the published ceilings so this gate trips before the
# provider's does. Gemini publishes no hourly or daily token cap, so TPH/TPD are
# derived from RPD × a generous per-call budget. Re-tune these when changing
# AI_BASE_URL — confirm the real numbers in the provider's console.
#
# MAX_CONTEXT_TOKENS is NOT the model's context window (Gemini accepts 1M); it is
# a runaway-input guard that rejects absurd prompts before the network call.
MAX_CONTEXT_TOKENS = 128_000
MAX_RPM, MAX_RPH, MAX_RPD = 8, 400, 1_200
MAX_TPM, MAX_TPH, MAX_TPD = 200_000, 2_000_000, 4_000_000
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
    """Token entry held in the window; `commit` mutates `tokens` in place."""

    timestamp: float
    tokens: int


class GlobalRateLimiter:
    def __init__(self) -> None:
        self._requests: deque[float] = deque()
        self._tokens: deque[Reservation] = deque()
        self._lock = asyncio.Lock()

    def _evict(self, now: float) -> None:
        cutoff = now - WINDOW_24H
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        while self._tokens and self._tokens[0].timestamp < cutoff:
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

            tpm = sum(r.tokens for r in self._tokens if r.timestamp >= now - WINDOW_1M)
            tph = sum(r.tokens for r in self._tokens if r.timestamp >= now - WINDOW_1H)
            tpd = sum(r.tokens for r in self._tokens)

            if tpm + estimated_tokens > MAX_TPM:
                oldest = next(
                    r.timestamp for r in self._tokens if r.timestamp >= now - WINDOW_1M
                )
                raise LocalRateLimitError("tpm", WINDOW_1M - (now - oldest))
            if tph + estimated_tokens > MAX_TPH:
                oldest = next(
                    r.timestamp for r in self._tokens if r.timestamp >= now - WINDOW_1H
                )
                raise LocalRateLimitError("tph", WINDOW_1H - (now - oldest))
            if tpd + estimated_tokens > MAX_TPD:
                raise LocalRateLimitError(
                    "tpd", WINDOW_24H - (now - self._tokens[0].timestamp)
                )

            self._requests.append(now)
            entry = Reservation(timestamp=now, tokens=estimated_tokens)
            self._tokens.append(entry)
            return entry

    def commit(self, reservation: Reservation, actual_tokens: int) -> None:
        """Replace the reservation's estimate with actual usage post-call."""
        reservation.tokens = actual_tokens


_limiter: GlobalRateLimiter | None = None


def get_limiter() -> GlobalRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = GlobalRateLimiter()
    return _limiter
