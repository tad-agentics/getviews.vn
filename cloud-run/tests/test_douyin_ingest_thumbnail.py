"""PR-D — Douyin ingest: per-row thumbnail step (R2-frame-first).

The Vietnamese ``corpus_ingest`` pipeline (PR #282) wires
``copy_first_frame_to_thumbnail`` between row build and upsert so the
permanent ``thumbnail_url`` written to ``video_corpus`` is an R2 URL,
not a stale platform CDN URL. Same architecture for Douyin: frame[0]
is already in R2 from ``extract_and_upload`` during analysis, so a
single server-side ``copy_object`` clones it into the
``thumbnails/{vid}.png`` namespace.

These tests exercise ``_ingest_candidate_awemes_douyin`` end-to-end
with everything mocked except the thumbnail decision logic, asserting:

  • R2 frame[0] copy chosen when hook_frames present (douyinpic.com
    never touched).
  • CDN mirror fallback when hook_frames empty (frame extraction
    failed for that row → only the platform URL is left to mirror).
  • ``r2_configured() = False`` short-circuits the whole step (CI /
    local dev without R2 creds keeps working).
  • The R2 URL is patched onto the row BEFORE the corpus upsert so
    the persisted ``thumbnail_url`` is the R2 one, not the platform
    CDN one.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from getviews_pipeline.douyin_ingest import _ingest_candidate_awemes_douyin

# ── Test scaffolding ────────────────────────────────────────────────


def _aweme(vid: str) -> dict[str, Any]:
    """Minimal aweme — quality gates already passed before this point."""
    return {"aweme_id": vid}


def _row(vid: str, *, thumbnail_url: str | None) -> dict[str, Any]:
    """Minimal corpus-row dict — the upsert path doesn't care about
    other columns in these tests."""
    return {"video_id": vid, "thumbnail_url": thumbnail_url}


def _patch_pipeline(
    *,
    rows_with_frames: list[tuple[dict[str, Any], list[str]]],
    r2_configured: bool = True,
    frame_copy_returns: str | None | type = "default",
    cdn_mirror_returns: str | None = None,
):
    """Patches ``_analyze_translate_one``, ``build_douyin_corpus_row``,
    upserts, ``r2_configured``, and the two thumbnail helpers with the
    given controls.

    rows_with_frames: ordered list of (row, hook_frames) tuples — each
    represents one candidate aweme; ``hook_frames=[]`` simulates a row
    where frame extraction failed.
    """
    captured: dict[str, Any] = {
        "frame_copy_calls": [],
        "cdn_mirror_calls": [],
        "upserted_rows": None,
    }

    # Pre-baked return tuples for _analyze_translate_one — order
    # matches the candidate order; analysis & translation contents
    # don't matter, only the hook_frames column.
    return_tuples = [
        ({"analysis": {"scenes": []}}, frames, [], "translation")
        for _, frames in rows_with_frames
    ]
    rows_in_order = [r for r, _ in rows_with_frames]

    def _frame_copy_side_effect(vid: str):
        captured["frame_copy_calls"].append(vid)
        if frame_copy_returns == "default":
            return f"https://r2.test/thumbnails/{vid}.png"
        return frame_copy_returns

    async def _cdn_mirror_side_effect(url: str, vid: str):
        captured["cdn_mirror_calls"].append((url, vid))
        return cdn_mirror_returns

    def _capture_upsert(_client, rows):
        captured["upserted_rows"] = [dict(r) for r in rows]

    def _capture_shots(_client, _shot_rows):
        return (True, None)

    return captured, patch.multiple(
        "getviews_pipeline.douyin_ingest",
        _analyze_translate_one=AsyncMock(side_effect=return_tuples),
        build_douyin_corpus_row=MagicMock(side_effect=rows_in_order),
        build_douyin_shot_rows=MagicMock(return_value=[]),
        _upsert_douyin_corpus_rows_sync=MagicMock(side_effect=_capture_upsert),
        _upsert_douyin_shots_with_retry_sync=MagicMock(
            side_effect=_capture_shots
        ),
        r2_configured=MagicMock(return_value=r2_configured),
        copy_first_frame_to_thumbnail=MagicMock(
            side_effect=_frame_copy_side_effect
        ),
        download_and_upload_thumbnail=AsyncMock(
            side_effect=_cdn_mirror_side_effect
        ),
    )


# ── 1. Frame[0] present → R2 copy chosen, CDN never touched ────────


@pytest.mark.asyncio
async def test_frame_copy_chosen_when_hook_frames_present() -> None:
    """When ``extract_and_upload`` succeeded earlier in the pipeline
    (hook_frames non-empty), the thumbnail must come from a server-side
    R2 copy of frame[0] — the douyinpic.com CDN must NOT be hit."""
    row = _row("v1", thumbnail_url="https://douyinpic.com/old.jpg")
    captured, patcher = _patch_pipeline(
        rows_with_frames=[(row, ["https://r2.test/frames/v1/0.png"])],
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v1")],
        )

    assert result.inserted == 1
    assert captured["frame_copy_calls"] == ["v1"]
    assert captured["cdn_mirror_calls"] == []
    # Most important: the R2 URL is the one we persist, not the
    # platform CDN URL on the row at build time.
    assert captured["upserted_rows"] is not None
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://r2.test/thumbnails/v1.png"
    )


# ── 2. No frame → CDN mirror fallback ──────────────────────────────


@pytest.mark.asyncio
async def test_cdn_mirror_fallback_when_no_hook_frames() -> None:
    """If frame extraction failed (hook_frames empty), the only source
    for the thumbnail is the platform CDN URL — fall back to mirror."""
    row = _row("v2", thumbnail_url="https://douyinpic.com/cover.jpg")
    captured, patcher = _patch_pipeline(
        rows_with_frames=[(row, [])],  # frame extraction failed
        cdn_mirror_returns="https://r2.test/thumbnails/v2.jpg",
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v2")],
        )

    assert result.inserted == 1
    assert captured["frame_copy_calls"] == []
    assert captured["cdn_mirror_calls"] == [
        ("https://douyinpic.com/cover.jpg", "v2"),
    ]
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://r2.test/thumbnails/v2.jpg"
    )


# ── 3. CDN mirror returns None → row keeps its platform URL ────────


@pytest.mark.asyncio
async def test_cdn_mirror_failure_leaves_platform_url() -> None:
    """If the CDN mirror returns None (douyinpic.com rejected the
    TikTok-shaped Referer, say), the row keeps its existing
    platform URL. The FE's <VideoThumbnail> handles broken URLs
    gracefully via onError."""
    row = _row("v3", thumbnail_url="https://douyinpic.com/cover.jpg")
    captured, patcher = _patch_pipeline(
        rows_with_frames=[(row, [])],
        cdn_mirror_returns=None,
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v3")],
        )

    assert result.inserted == 1
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://douyinpic.com/cover.jpg"
    )


# ── 4. Mixed batch — frame for some, CDN for others ────────────────


@pytest.mark.asyncio
async def test_mixed_batch_picks_correct_path_per_row() -> None:
    """Two-row batch: row A has frames, row B doesn't. Each row picks
    its own path independently — no cross-contamination."""
    rowA = _row("vA", thumbnail_url="https://douyinpic.com/a.jpg")
    rowB = _row("vB", thumbnail_url="https://douyinpic.com/b.jpg")
    captured, patcher = _patch_pipeline(
        rows_with_frames=[
            (rowA, ["https://r2.test/frames/vA/0.png"]),
            (rowB, []),
        ],
        cdn_mirror_returns="https://r2.test/thumbnails/vB.jpg",
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(),
            {"id": 1, "slug": "wellness"},
            [_aweme("vA"), _aweme("vB")],
        )

    assert result.inserted == 2
    assert captured["frame_copy_calls"] == ["vA"]
    assert captured["cdn_mirror_calls"] == [
        ("https://douyinpic.com/b.jpg", "vB"),
    ]
    upserted_by_id = {r["video_id"]: r for r in captured["upserted_rows"]}
    assert upserted_by_id["vA"]["thumbnail_url"] == (
        "https://r2.test/thumbnails/vA.png"
    )
    assert upserted_by_id["vB"]["thumbnail_url"] == (
        "https://r2.test/thumbnails/vB.jpg"
    )


# ── 5. r2_configured() False → step skipped entirely ───────────────


@pytest.mark.asyncio
async def test_r2_unconfigured_short_circuits_thumbnail_step() -> None:
    """In CI / local dev without R2 creds, the thumbnail step must
    be a complete no-op — no helper calls, row keeps its platform URL.
    Skipping silently keeps the rest of the ingest pipeline runnable
    without R2 setup."""
    row = _row("v4", thumbnail_url="https://douyinpic.com/cover.jpg")
    captured, patcher = _patch_pipeline(
        rows_with_frames=[(row, ["https://r2.test/frames/v4/0.png"])],
        r2_configured=False,
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v4")],
        )

    assert result.inserted == 1
    assert captured["frame_copy_calls"] == []
    assert captured["cdn_mirror_calls"] == []
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://douyinpic.com/cover.jpg"
    )


# ── 6. Frame copy raising → row keeps platform URL, batch continues ─


@pytest.mark.asyncio
async def test_frame_copy_exception_isolated_per_row() -> None:
    """If the executor wraps an exception (R2 client blew up etc.),
    one row's failure must NOT poison the rest of the batch. The
    failed row keeps its platform URL; the other rows process
    normally."""
    rowA = _row("vA", thumbnail_url="https://douyinpic.com/a.jpg")
    rowB = _row("vB", thumbnail_url="https://douyinpic.com/b.jpg")
    captured: dict[str, Any] = {"upserted_rows": None}

    def _frame_copy_side_effect(vid: str):
        if vid == "vA":
            raise RuntimeError("R2 client exploded")
        return f"https://r2.test/thumbnails/{vid}.png"

    def _capture_upsert(_client, rows):
        captured["upserted_rows"] = [dict(r) for r in rows]

    return_tuples = [
        ({"analysis": {"scenes": []}}, ["frame"], [], "tr"),
        ({"analysis": {"scenes": []}}, ["frame"], [], "tr"),
    ]

    with patch.multiple(
        "getviews_pipeline.douyin_ingest",
        _analyze_translate_one=AsyncMock(side_effect=return_tuples),
        build_douyin_corpus_row=MagicMock(side_effect=[rowA, rowB]),
        build_douyin_shot_rows=MagicMock(return_value=[]),
        _upsert_douyin_corpus_rows_sync=MagicMock(side_effect=_capture_upsert),
        _upsert_douyin_shots_with_retry_sync=MagicMock(
            return_value=(True, None)
        ),
        r2_configured=MagicMock(return_value=True),
        copy_first_frame_to_thumbnail=MagicMock(
            side_effect=_frame_copy_side_effect
        ),
        download_and_upload_thumbnail=AsyncMock(return_value=None),
    ):
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(),
            {"id": 1, "slug": "wellness"},
            [_aweme("vA"), _aweme("vB")],
        )

    assert result.inserted == 2
    upserted_by_id = {r["video_id"]: r for r in captured["upserted_rows"]}
    # Failed row keeps its platform URL.
    assert upserted_by_id["vA"]["thumbnail_url"] == (
        "https://douyinpic.com/a.jpg"
    )
    # The other row still healed.
    assert upserted_by_id["vB"]["thumbnail_url"] == (
        "https://r2.test/thumbnails/vB.png"
    )
