"""Runtime utilities for Cloud Run.

run_sync wraps sync Gemini SDK calls in a thread pool to keep the
asyncio event loop unblocked. The analysis semaphore caps concurrent
Gemini calls per instance.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable

_ANALYSIS_SEMAPHORE: asyncio.Semaphore | None = None


async def run_sync(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


def get_analysis_semaphore() -> asyncio.Semaphore:
    """Limit concurrent Gemini calls per Cloud Run instance.

    Default 4 — fits 1 vCPU with Gemini calls being I/O-bound.
    Override via GEMINI_CONCURRENCY env var.
    """
    global _ANALYSIS_SEMAPHORE
    if _ANALYSIS_SEMAPHORE is None:
        limit = int(os.environ.get("GEMINI_CONCURRENCY", "4"))
        _ANALYSIS_SEMAPHORE = asyncio.Semaphore(limit)
    return _ANALYSIS_SEMAPHORE
