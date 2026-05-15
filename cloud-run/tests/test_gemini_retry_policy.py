"""Retry classifier — 429 is NOT transient, only 503/overloaded is.

Pins the cost-driven decision that 429 RESOURCE_EXHAUSTED must fail fast.
Google bills input tokens on every failed attempt; retrying a rate-limit
with 1s/2s/4s sleeps bills the same prompt 4× and amplifies a throttle
into a bill spike. 503/overloaded is still retried because it's a Google
backend hiccup, not a quota signal.
"""

from __future__ import annotations

import pytest

pytest.importorskip("google.genai")

from getviews_pipeline.gemini import _is_transient_gemini_error  # noqa: E402


def test_429_is_not_retried() -> None:
    # All of these mean "Google is already throttling you" — retrying
    # rebills input tokens for nothing.
    assert not _is_transient_gemini_error(Exception("429 Too Many Requests"))
    assert not _is_transient_gemini_error(Exception("RESOURCE_EXHAUSTED: quota exceeded"))
    assert not _is_transient_gemini_error(Exception("rate limit exceeded for model"))


def test_503_overloaded_is_retried() -> None:
    # Backend transient — retry is correct.
    assert _is_transient_gemini_error(Exception("503 Service Unavailable"))
    assert _is_transient_gemini_error(Exception("model is overloaded, please try again"))


def test_non_transient_errors_not_retried() -> None:
    # Programmer errors / 4xx other than 429: don't burn retries.
    assert not _is_transient_gemini_error(Exception("400 Bad Request: invalid argument"))
    assert not _is_transient_gemini_error(ValueError("schema mismatch"))
