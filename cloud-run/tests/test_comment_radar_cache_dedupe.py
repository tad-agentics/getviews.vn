"""BUG-09 regression (QA audit 2026-04-22): the per-video asyncio lock
in ``resolve_comment_radar`` collapses concurrent fetches so two
parallel callers (the win-mode + flop-mode analyse calls fired together
by VideoScreen) return the same radar instead of diverging from
independent EnsembleData samples.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import getviews_pipeline.comment_radar_cache as cache_mod


@pytest.fixture(autouse=True)
def _clear_locks() -> None:
    cache_mod._FETCH_LOCKS.clear()
    cache_mod._INFLIGHT_RESULTS.clear()


@pytest.mark.asyncio
async def test_concurrent_callers_share_one_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two concurrent ``resolve_comment_radar`` calls for the same video
    must produce a single underlying fetch + writeback so both callers
    see identical percentages (BUG-09)."""
    fetch_calls = 0
    write_calls: list[dict[str, Any]] = []

    # Anon client unavailable → skips the initial cache read, forcing the
    # lock-guarded fetch path we want to exercise.
    def _no_anon_client() -> None:
        raise RuntimeError("no anon client in this test")

    monkeypatch.setattr(
        "getviews_pipeline.corpus_context._anon_client", _no_anon_client, raising=False,
    )

    async def _fake_fetch(video_id: str, *, max_comments: int = 50) -> list[str]:
        nonlocal fetch_calls
        fetch_calls += 1
        # Simulate the EnsembleData round-trip taking real wall time so
        # the second caller actually parks on the lock instead of racing.
        await asyncio.sleep(0.05)
        return ["Hay quá", "Video này chất", "Mua luôn", "Bình thường"]

    monkeypatch.setattr(
        "getviews_pipeline.comment_radar.fetch_comments_for_video", _fake_fetch,
    )

    def _fake_write(video_id: str, radar: dict[str, Any]) -> None:
        write_calls.append(dict(radar))

    monkeypatch.setattr(cache_mod, "_write_cached_sync", _fake_write)

    # No DB cache → both callers enter the lock.
    a, b = await asyncio.gather(
        cache_mod.resolve_comment_radar("vid-A", comment_count_hint=10),
        cache_mod.resolve_comment_radar("vid-A", comment_count_hint=10),
    )

    assert a is not None and b is not None
    assert a == b, "both concurrent callers must see identical radar"
    assert fetch_calls == 1, "the fetch must happen exactly once per video"


@pytest.mark.asyncio
async def test_lock_is_per_video(monkeypatch: pytest.MonkeyPatch) -> None:
    """Different video_ids keep independent locks — no cross-video
    serialisation (a global lock would serialise the whole corpus)."""

    def _no_anon_client() -> None:
        raise RuntimeError("no anon client in this test")

    monkeypatch.setattr(
        "getviews_pipeline.corpus_context._anon_client", _no_anon_client, raising=False,
    )

    async def _fake_fetch(video_id: str, *, max_comments: int = 50) -> list[str]:
        return ["Hay quá", "Mua luôn"]

    monkeypatch.setattr(
        "getviews_pipeline.comment_radar.fetch_comments_for_video", _fake_fetch,
    )
    monkeypatch.setattr(cache_mod, "_write_cached_sync", lambda *_a, **_k: None)

    await asyncio.gather(
        cache_mod.resolve_comment_radar("vid-A", comment_count_hint=10),
        cache_mod.resolve_comment_radar("vid-B", comment_count_hint=10),
    )
    assert "vid-A" in cache_mod._FETCH_LOCKS
    assert "vid-B" in cache_mod._FETCH_LOCKS
    assert cache_mod._FETCH_LOCKS["vid-A"] is not cache_mod._FETCH_LOCKS["vid-B"]
