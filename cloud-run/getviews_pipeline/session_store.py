"""SSE replay buffer for Cloud Run answer_turn streams (TD-4).

In-process and best-effort — a reconnect to a different instance gets a
fresh stream rather than a replay. Acceptable at MVP scale.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# CLAUDE.md TD-4: 60s replay window. Past this the client's reconnect
# attempt falls through to a fresh stream rather than a replay.
_STREAM_REPLAY_TTL_SEC = 60.0
# How often the background sweeper runs. Half the TTL keeps mean
# residency for an expired entry under one TTL window without
# burning CPU.
_REPLAY_SWEEP_INTERVAL_SEC = 30.0
_stream_chunks: dict[str, dict[str, Any]] = {}


def _normalise_chunk_items(
    chunks: list[str] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Accept either bare strings (legacy callers) or seq-stamped dicts."""
    out: list[dict[str, Any]] = []
    for i, item in enumerate(chunks, start=1):
        if isinstance(item, dict):
            if "seq" not in item:
                item = {**item, "seq": i}
            out.append(item)
        else:
            out.append({"seq": i, "delta": str(item)})
    return out


def put_stream_chunks(
    stream_id: str,
    chunks: list[str] | list[dict[str, Any]],
) -> None:
    """Cache token items for reconnect replay."""
    _stream_chunks[stream_id] = {
        "chunks": _normalise_chunk_items(chunks),
        "expires_at": time.monotonic() + _STREAM_REPLAY_TTL_SEC,
    }


def get_stream_chunks(stream_id: str) -> list[dict[str, Any]] | None:
    """Return cached seq-stamped chunk items, or ``None`` on miss/expiry."""
    entry = _stream_chunks.get(stream_id)
    if not entry:
        return None
    if time.monotonic() > float(entry["expires_at"]):
        _stream_chunks.pop(stream_id, None)
        return None
    return [dict(item) for item in entry["chunks"]]


def sweep_expired_stream_chunks(now: float | None = None) -> int:
    """Drop every replay entry whose TTL has passed."""
    cutoff = now if now is not None else time.monotonic()
    expired = [sid for sid, entry in _stream_chunks.items() if cutoff > float(entry["expires_at"])]
    for sid in expired:
        _stream_chunks.pop(sid, None)
    return len(expired)


async def replay_buffer_sweeper(interval: float = _REPLAY_SWEEP_INTERVAL_SEC) -> None:
    """Long-running coroutine that periodically prunes the replay buffer."""
    while True:
        try:
            removed = sweep_expired_stream_chunks()
            if removed:
                logger.info("[replay-buffer] swept %d expired entries", removed)
            else:
                logger.debug("[replay-buffer] sweep ran, no entries expired")
        except Exception as exc:
            logger.warning("[replay-buffer] sweep failed: %s", exc)
        await asyncio.sleep(interval)
