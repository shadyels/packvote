import time
from collections import deque


class SlidingWindow:
    """Allow at most `max_events` hits per rolling `window_s` seconds.

    Methods are synchronous, so each is atomic under single-threaded asyncio.
    A separate allowed() then hit() is atomic only if the caller puts no await
    between them; otherwise use acquire().
    """

    def __init__(self, max_events: int, window_s: float) -> None:
        self._max = max_events
        self._window = window_s
        self._events: deque[float] = deque()

    def _evict(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] <= cutoff:
            self._events.popleft()

    def allowed(self) -> bool:
        self._evict(time.monotonic())
        return len(self._events) < self._max

    def hit(self) -> None:
        now = time.monotonic()
        self._evict(now)
        self._events.append(now)

    def acquire(self) -> bool:
        """Check and record in one step; False (nothing recorded) if full."""
        now = time.monotonic()
        self._evict(now)
        if len(self._events) >= self._max:
            return False
        self._events.append(now)
        return True
