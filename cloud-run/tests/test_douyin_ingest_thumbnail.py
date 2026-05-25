"""PR-D — Douyin ingest: per-row thumbnail step (WebP via ``resolve_ingest_thumbnail_url``).

The Vietnamese ``corpus_ingest`` pipeline wires ``resolve_ingest_thumbnail_url``
between row build and upsert so the permanent ``thumbnail_url`` written to
``video_corpus`` is an R2 WebP URL, not a stale platform CDN URL or legacy
R2 ``.png`` pointer.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from getviews_pipeline.douyin_ingest import _ingest_candidate_awemes_douyin


def _aweme(vid: str) -> dict[str, Any]:
    return {"aweme_id": vid}


def _row(vid: str, *, thumbnail_url: str | None) -> dict[str, Any]:
    return {"video_id": vid, "thumbnail_url": thumbnail_url}


def _patch_pipeline(
    *,
    rows: list[dict[str, Any]],
    hook_frames_by_row: list[list[str]],
    r2_configured: bool = True,
    resolve_returns: str | None | type = "default",
):
    captured: dict[str, Any] = {"resolve_calls": [], "upserted_rows": None}

    return_tuples = [
        ({"analysis": {"scenes": []}}, frames, [], "translation")
        for frames in hook_frames_by_row
    ]

    async def _resolve_side_effect(vid: str, existing: str | None):
        captured["resolve_calls"].append((vid, existing))
        if resolve_returns == "default":
            return f"https://r2.test/thumbnails/{vid}.webp"
        return resolve_returns

    def _capture_upsert(_client, upsert_rows):
        captured["upserted_rows"] = [dict(r) for r in upsert_rows]

    patcher = patch.multiple(
        "getviews_pipeline.douyin_ingest",
        _analyze_translate_one=AsyncMock(side_effect=return_tuples),
        build_douyin_corpus_row=MagicMock(side_effect=rows),
        build_douyin_shot_rows=MagicMock(return_value=[]),
        _upsert_douyin_corpus_rows_sync=MagicMock(side_effect=_capture_upsert),
        _upsert_douyin_shots_with_retry_sync=MagicMock(return_value=(True, None)),
        r2_configured=MagicMock(return_value=r2_configured),
        resolve_ingest_thumbnail_url=AsyncMock(side_effect=_resolve_side_effect),
    )
    return captured, patcher


@pytest.mark.asyncio
async def test_resolve_called_with_platform_cdn_url() -> None:
    row = _row("v1", thumbnail_url="https://douyinpic.com/old.jpg")
    captured, patcher = _patch_pipeline(
        rows=[row],
        hook_frames_by_row=[["https://r2.test/frames/v1/0.png"]],
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v1")],
        )

    assert result.inserted == 1
    assert captured["resolve_calls"] == [("v1", "https://douyinpic.com/old.jpg")]
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://r2.test/thumbnails/v1.webp"
    )


@pytest.mark.asyncio
async def test_resolve_failure_leaves_platform_url() -> None:
    row = _row("v3", thumbnail_url="https://douyinpic.com/cover.jpg")
    captured, patcher = _patch_pipeline(
        rows=[row],
        hook_frames_by_row=[[]],
        resolve_returns=None,
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v3")],
        )

    assert result.inserted == 1
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://douyinpic.com/cover.jpg"
    )


@pytest.mark.asyncio
async def test_mixed_batch_resolves_each_row() -> None:
    rowA = _row("vA", thumbnail_url="https://douyinpic.com/a.jpg")
    rowB = _row("vB", thumbnail_url="https://pub-abc.r2.dev/thumbnails/vB.png")
    captured, patcher = _patch_pipeline(rows=[rowA, rowB], hook_frames_by_row=[[], []])
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(),
            {"id": 1, "slug": "wellness"},
            [_aweme("vA"), _aweme("vB")],
        )

    assert result.inserted == 2
    assert captured["resolve_calls"] == [
        ("vA", "https://douyinpic.com/a.jpg"),
        ("vB", "https://pub-abc.r2.dev/thumbnails/vB.png"),
    ]


@pytest.mark.asyncio
async def test_r2_unconfigured_skips_resolve() -> None:
    row = _row("v4", thumbnail_url="https://douyinpic.com/cover.jpg")
    captured, patcher = _patch_pipeline(
        rows=[row],
        hook_frames_by_row=[["https://r2.test/frames/v4/0.png"]],
        r2_configured=False,
    )
    with patcher:
        result = await _ingest_candidate_awemes_douyin(
            MagicMock(), {"id": 1, "slug": "wellness"}, [_aweme("v4")],
        )

    assert result.inserted == 1
    assert captured["resolve_calls"] == []
    assert captured["upserted_rows"][0]["thumbnail_url"] == (
        "https://douyinpic.com/cover.jpg"
    )
