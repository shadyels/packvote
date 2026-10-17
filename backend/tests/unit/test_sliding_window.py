from unittest.mock import patch

from app.services.rate_limit import SlidingWindow

MAX = 3
WINDOW = 100.0


def _mono(t: float):  # type: ignore[no-untyped-def]
    return patch("app.services.rate_limit.time.monotonic", return_value=t)


def test_acquire_blocks_after_max_and_records_nothing_when_full() -> None:
    w = SlidingWindow(MAX, WINDOW)
    assert [w.acquire() for _ in range(MAX + 2)] == [True] * MAX + [False] * 2
    assert not w.allowed()


def test_allowed_does_not_record_but_hit_does() -> None:
    w = SlidingWindow(1, WINDOW)
    assert w.allowed()
    assert w.allowed()
    w.hit()
    assert not w.allowed()


def test_window_expiry() -> None:
    w = SlidingWindow(MAX, WINDOW)
    with _mono(1000.0):
        for _ in range(MAX):
            w.hit()
        assert not w.acquire()
    with _mono(1000.0 + WINDOW - 1):
        assert not w.allowed()
    with _mono(1000.0 + WINDOW + 1):
        assert w.acquire()
