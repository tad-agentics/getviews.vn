"""M4 — SSE step_error event.

Pipelines wrap their try/finally with an except branch that emits a
``step_error`` before re-raising. This test pins the event shape and
the helper's behaviour so the frontend StepEvent union doesn't drift.
"""

from __future__ import annotations

import asyncio

import pytest

from getviews_pipeline.step_events import (
    DEFAULT_ERROR_MESSAGE_VI,
    emit_pipeline_error,
    emit_sentinel,
    step_error,
)


def test_step_error_default_shape() -> None:
    e = step_error()
    assert e["type"] == "step_error"
    assert e["code"] == "pipeline_failed"
    assert e["message_vi"] == DEFAULT_ERROR_MESSAGE_VI
    assert "detail" not in e


def test_step_error_custom_code_and_message() -> None:
    e = step_error(code="synthesis_failed", message_vi="Không tổng hợp được")
    assert e["code"] == "synthesis_failed"
    assert e["message_vi"] == "Không tổng hợp được"


def test_step_error_includes_detail_when_provided() -> None:
    e = step_error(detail="ValueError")
    assert e["detail"] == "ValueError"


@pytest.mark.asyncio
async def test_emit_pipeline_error_writes_to_queue() -> None:
    q: asyncio.Queue = asyncio.Queue()
    emit_pipeline_error(q, RuntimeError("boom"), code="synthesis_failed")
    event = q.get_nowait()
    assert event["type"] == "step_error"
    assert event["code"] == "synthesis_failed"
    # Exception class name surfaces as `detail` for ops debugging.
    assert event["detail"] == "RuntimeError"
    # Vietnamese fallback message used when the caller didn't pass one.
    assert event["message_vi"] == DEFAULT_ERROR_MESSAGE_VI


@pytest.mark.asyncio
async def test_emit_pipeline_error_is_noop_when_queue_is_none() -> None:
    # Pipelines may run without a step_queue (e.g. CLI / batch); the
    # helper must accept None silently.
    emit_pipeline_error(None, RuntimeError("boom"))


@pytest.mark.asyncio
async def test_pipeline_pattern_sequence_error_then_sentinel() -> None:
    """The documented pattern: error event lands BEFORE the sentinel,
    so the SSE generator processes the error and then terminates."""
    q: asyncio.Queue = asyncio.Queue()
    try:
        raise ValueError("synthesis blew up")
    except ValueError as exc:
        emit_pipeline_error(q, exc, code="synthesis_failed")
    finally:
        await emit_sentinel(q)

    first = q.get_nowait()
    second = q.get_nowait()
    assert first["type"] == "step_error"
    assert first["code"] == "synthesis_failed"
    assert first["detail"] == "ValueError"
    assert second is None  # sentinel
