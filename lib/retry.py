"""Small resilience helpers — polling and retry with exponential backoff.

Pure Python, no Databricks imports, so it is unit-testable in CI. Used by the
long-running provisioning steps (index readiness, endpoint creation) instead of
naive fixed-interval ``time.sleep`` loops.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def wait_until(
    check: Callable[[], T | None],
    *,
    timeout_s: float,
    interval_s: float = 15.0,
    max_interval_s: float = 60.0,
    backoff: float = 1.5,
    on_wait: Callable[[float], None] | None = None,
) -> T:
    """Poll ``check`` until it returns a truthy value, with capped backoff.

    ``check`` returns the result when ready, or a falsy value to keep waiting.
    Raises ``TimeoutError`` if the deadline passes first. ``on_wait`` (if given)
    is called with the next sleep interval — useful for progress logging.
    """
    deadline = time.monotonic() + timeout_s
    delay = interval_s
    while True:
        result = check()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Condition not met within {timeout_s:.0f}s")
        if on_wait:
            on_wait(delay)
        time.sleep(delay)
        delay = min(delay * backoff, max_interval_s)


def retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    interval_s: float = 2.0,
    backoff: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Call ``fn``, retrying on ``retry_on`` with exponential backoff.

    Re-raises the last exception once ``attempts`` is exhausted.
    """
    delay = interval_s
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:  # noqa: PERF203
            last = e
            if i == attempts - 1:
                break
            time.sleep(delay)
            delay *= backoff
    assert last is not None
    raise last
