"""One absolute deadline propagated through synchronous operation stages."""

import time
from contextlib import contextmanager
from contextvars import ContextVar

from app.core.errors import DeadlineExceeded

_deadline: ContextVar[float | None] = ContextVar("operation_deadline", default=None)


@contextmanager
def operation_deadline(seconds: float):
    token = _deadline.set(time.monotonic() + seconds)
    try:
        yield
    finally:
        _deadline.reset(token)


def remaining_timeout(maximum: float | None = None) -> float:
    deadline = _deadline.get()
    if deadline is None:
        if maximum is None:
            raise RuntimeError("No deadline or maximum configured")
        return maximum
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise DeadlineExceeded()
    return min(remaining, maximum) if maximum is not None else remaining


def check_deadline():
    if _deadline.get() is not None:
        remaining_timeout()
