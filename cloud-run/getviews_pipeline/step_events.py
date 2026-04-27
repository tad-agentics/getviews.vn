"""Step event helpers for the P0-6 Agentic Step Logger.

Pipeline functions receive an optional ``step_queue: asyncio.Queue | None`` parameter.
When set, they emit step event dicts onto the queue. The /stream handler reads from
the queue and yields SSE tokens before and during synthesis.

Event schema (mirrors src/lib/types/sse-events.ts):

    {"type": "step_start",   "label": "Đang phân tích video..."}
    {"type": "step_search",  "source": "tiktok"|"corpus", "query": "..."}
    {"type": "step_creator", "handle": "@creator"}
    {"type": "step_count",   "count": 120, "thumbnails": ["url1", ...]}
    {"type": "step_process", "label": "Đang tổng hợp chiến lược..."}
    {"type": "step_done",    "summary": "Phân tích xong — đang viết..."}
    {"type": "step_error",   "code": "synthesis_failed",
                              "message_vi": "Phân tích bị gián đoạn. Vui lòng thử lại."}

Usage pattern in a pipeline function:
    async def run_video_diagnosis(url, session, *, step_queue=None, ...):
        emit(step_queue, step_start("Đang tải video..."))
        ...
        emit(step_queue, step_search("corpus", "skincare vietnam"))
        ...
        emit(step_queue, step_done("Phân tích xong — đang viết báo cáo..."))

The sentinel value ``None`` is placed on the queue when the pipeline completes
(or fails) to signal the SSE generator that step events are finished.
"""

from __future__ import annotations

import asyncio
from typing import Any


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------

def step_start(label: str) -> dict[str, Any]:
    """Phase header — shown with rotating spinner."""
    return {"type": "step_start", "label": label}


def step_search(source: str, query: str) -> dict[str, Any]:
    """Search event — Vietnamese query displayed in quotes below the header.

    source: "tiktok" | "corpus" | "ensemble"
    """
    return {"type": "step_search", "source": source, "query": query}


def step_creator(handle: str) -> dict[str, Any]:
    """Creator discovery — purple handle shown with margin-left."""
    h = handle if handle.startswith("@") else f"@{handle}"
    return {"type": "step_creator", "handle": h}


def step_count(count: int, thumbnails: list[str] | None = None) -> dict[str, Any]:
    """Count line — 'Đã tìm X video' + optional circular thumbnail previews."""
    return {"type": "step_count", "count": count, "thumbnails": thumbnails or []}


def step_process(label: str) -> dict[str, Any]:
    """Processing event — shown with rotating spinner (secondary phase)."""
    return {"type": "step_process", "label": label}


def step_done(summary: str) -> dict[str, Any]:
    """Phase complete — collapses children to '✓' line, shows summary."""
    return {"type": "step_done", "summary": summary}


# Vietnamese-language fallback message used by every step_error emission.
# Keeping this here means the wording is consistent across pipelines and
# isn't hand-rewritten next to each try/except.
DEFAULT_ERROR_MESSAGE_VI = (
    "Phân tích bị gián đoạn. Vui lòng thử lại sau ít phút."
)


def step_error(
    code: str = "pipeline_failed",
    message_vi: str | None = None,
    *,
    detail: str | None = None,
) -> dict[str, Any]:
    """Mid-stream pipeline failure — frontend should render a graceful
    "phân tích bị gián đoạn" state instead of leaving the spinner running
    forever.

    ``code`` is a machine-readable label (e.g. ``"synthesis_failed"``,
    ``"gemini_timeout"``, ``"budget_exceeded"``). ``message_vi`` is the
    Vietnamese sentence the UI shows; defaults to a generic line so callers
    can emit fast without crafting copy. ``detail`` is optional debug
    context — included for ops; the UI may hide it.
    """
    event: dict[str, Any] = {
        "type": "step_error",
        "code": code,
        "message_vi": message_vi or DEFAULT_ERROR_MESSAGE_VI,
    }
    if detail:
        event["detail"] = detail
    return event


# ---------------------------------------------------------------------------
# Emit helper — safe fire-and-forget into queue (never blocks the pipeline)
# ---------------------------------------------------------------------------

def emit(queue: asyncio.Queue | None, event: dict[str, Any]) -> None:
    """Put an event onto the step queue. No-op when queue is None.

    Uses put_nowait so it never blocks the pipeline. The queue is
    unbounded (maxsize=0 default) so this never raises QueueFull.
    """
    if queue is None:
        return
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        pass  # should never happen with unbounded queue


async def emit_sentinel(queue: asyncio.Queue | None) -> None:
    """Signal that step events are finished. Must be called in finally block."""
    if queue is None:
        return
    try:
        queue.put_nowait(None)  # None = sentinel
    except asyncio.QueueFull:
        pass


def emit_pipeline_error(
    queue: asyncio.Queue | None,
    exc: BaseException,
    *,
    code: str = "pipeline_failed",
    message_vi: str | None = None,
) -> None:
    """Convenience for ``except`` blocks: emit a ``step_error`` carrying
    the exception class name as ``detail`` so the client can render a
    "phân tích bị gián đoạn" state instead of a stuck spinner.

    Pair with ``emit_sentinel`` in ``finally`` so the SSE generator
    still terminates after the error event lands::

        try:
            ...
        except Exception as exc:
            emit_pipeline_error(step_queue, exc)
            raise
        finally:
            await emit_sentinel(step_queue)
    """
    emit(queue, step_error(code=code, message_vi=message_vi, detail=type(exc).__name__))
