"""Tests for lib/retry.py — polling and retry with backoff."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.retry import retry, wait_until  # noqa: E402


def test_wait_until_returns_when_ready(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)  # don't actually sleep
    calls = {"n": 0}

    def check():
        calls["n"] += 1
        return "ready" if calls["n"] >= 3 else None

    assert wait_until(check, timeout_s=100, interval_s=0.01) == "ready"
    assert calls["n"] == 3


def test_wait_until_times_out(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    # monotonic advances past the deadline after the first failed check.
    ticks = iter([0.0, 0.0, 5.0, 5.0, 10.0, 10.0])
    monkeypatch.setattr("time.monotonic", lambda: next(ticks, 100.0))
    with pytest.raises(TimeoutError):
        wait_until(lambda: None, timeout_s=1, interval_s=0.01)


def test_retry_succeeds_after_failures(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert retry(flaky, attempts=5, interval_s=0.01) == "ok"
    assert calls["n"] == 3


def test_retry_reraises_last(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    def always_fails():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        retry(always_fails, attempts=2, interval_s=0.01)
