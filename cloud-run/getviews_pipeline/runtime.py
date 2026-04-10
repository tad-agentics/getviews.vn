"""Runtime utilities for Cloud Run — replaces MCP semaphore with asyncio.

In Cloud Run, each request runs in its own process, so no cross-request
semaphore is needed. run_sync wraps sync Gemini SDK calls in a thread pool
to keep the asyncio event loop unblocked.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable


async def run_sync(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))


def get_analysis_semaphore() -> asyncio.Semaphore:
    """No-op in Cloud Run — returns an always-available semaphore."""
    return asyncio.Semaphore(999)
