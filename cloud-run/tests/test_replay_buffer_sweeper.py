"""TD-4 SSE replay buffer hygiene.

The lazy eviction inside ``get_stream_chunks`` only fires on lookup,
so an orphaned stream_id (client never reconnects) sat forever on
``min-instances=1`` pods. The active sweeper coroutine prunes
expired entries on a 30 s cadence.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from getviews_pipeline import session_store


def setup_function(_fn) -> None:
    session_store._stream_chunks.clear()  # type: ignore[attr-defined]


def teardown_function(_fn) -> None:
    session_store._stream_chunks.clear()  # type: ignore[attr-defined]


def test_ttl_matches_claudemd_60s() -> None:
    """CLAUDE.md TD-4 mandates 60 s — code must not drift."""
    assert session_store._STREAM_REPLAY_TTL_SEC == 60.0


def test_put_with_seq_dicts_round_trips_seq_verbatim() -> None:
    """M5 — buffer stores explicit seq per item so replay re-emits the
    same seq the client saw live (not list-index drift)."""
    items = [
        {"seq": 7, "delta": "alpha"},
        {"seq": 8, "delta": "beta"},
        {"seq": 9, "delta": "", "done": True},
    ]
    session_store.put_stream_chunks("stream-seq", items)
    out = session_store.get_stream_chunks("stream-seq")
    assert out == items


def test_put_with_legacy_strings_auto_stamps_seq() -> None:
    """Legacy callers that still pass list[str] keep working — auto-stamped
    seq=1..N. Removes the migration burden for low-traffic helpers."""
    session_store.put_stream_chunks("stream-legacy", ["a", "b", "c"])
    out = session_store.get_stream_chunks("stream-legacy")
    assert out is not None
    assert [item["seq"] for item in out] == [1, 2, 3]
    assert [item["delta"] for item in out] == ["a", "b", "c"]


def test_get_returns_copies_not_aliases() -> None:
    """Mutating the returned list / dicts must not corrupt the cache."""
    session_store.put_stream_chunks(
        "stream-copy", [{"seq": 1, "delta": "x"}]
    )
    first = session_store.get_stream_chunks("stream-copy")
    assert first is not None
    first[0]["delta"] = "MUTATED"
    second = session_store.get_stream_chunks("stream-copy")
    assert second is not None
    assert second[0]["delta"] == "x"


def test_sweep_drops_expired_entries() -> None:
    """``sweep_expired_stream_chunks`` returns # removed and prunes them."""
    session_store.put_stream_chunks("fresh", ["a", "b"])
    session_store.put_stream_chunks("stale", ["c"])

    # Force ``stale`` to look expired without sleeping for 60s.
    session_store._stream_chunks["stale"]["expires_at"] = time.monotonic() - 1

    removed = session_store.sweep_expired_stream_chunks()

    assert removed == 1
    assert "fresh" in session_store._stream_chunks
    assert "stale" not in session_store._stream_chunks


def test_sweep_with_no_expired_returns_zero() -> None:
    session_store.put_stream_chunks("fresh", ["a"])
    assert session_store.sweep_expired_stream_chunks() == 0
    assert "fresh" in session_store._stream_chunks


@pytest.mark.asyncio
async def test_sweeper_loop_runs_and_cancels_cleanly() -> None:
    """The lifespan-driven sweeper must prune entries and cancel cleanly."""
    session_store.put_stream_chunks("doomed", ["x"])
    session_store._stream_chunks["doomed"]["expires_at"] = time.monotonic() - 1

    # Tight interval so the test stays fast.
    task = asyncio.create_task(session_store.replay_buffer_sweeper(interval=0.05))
    await asyncio.sleep(0.12)  # at least one sweep tick

    assert "doomed" not in session_store._stream_chunks

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
