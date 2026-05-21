"""CR-3 — per-aweme niche_id for creator overrides (no loop variable mutation)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from getviews_pipeline import corpus_ingest as ci


@pytest.mark.asyncio
async def test_ingest_candidate_awemes_uses_per_aweme_stashed_niche(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second candidate keeps pool niche_id when first has a creator override."""
    nic_a = {
        "aweme_id": "111",
        "desc": "caption ví dụ",
        "author": {"unique_id": "andypham.academy", "region": "VN"},
        "statistics": {
            "play_count": 10_000,
            "digg_count": 100,
            "comment_count": 5,
            "share_count": 1,
        },
        "_ingest_niche_id": 5,  # CREATOR_NICHE_OVERRIDE for andypham.academy
    }
    nic_b = {
        "aweme_id": "222",
        "desc": "khác một chút ví dụ",
        "author": {"unique_id": "someone_else", "region": "VN"},
        "statistics": {
            "play_count": 10_000,
            "digg_count": 100,
            "comment_count": 5,
            "share_count": 1,
        },
    }

    async def fake_analyze_aweme(aweme: dict, **kwargs: object) -> dict:
        return {
            "metadata": {
                "author": {"username": "u"},
                "metrics": {"views": 100, "likes": 10, "comments": 1, "shares": 0},
            },
            "analysis": {"hook_analysis": {}, "scenes": []},
            "content_type": "carousel",
        }

    captured: list[int] = []

    def fake_build_corpus_row(
        aweme: dict,
        analysis: dict,
        niche_id: int,
        **kwargs: object,
    ) -> dict | None:
        captured.append(niche_id)
        return {
            "video_id": str(aweme.get("aweme_id")),
            "ingest_loop_niche_id": niche_id,
            "content_type": "carousel",
            "hashtags": [],
        }

    monkeypatch.setattr(ci, "analyze_aweme", fake_analyze_aweme)
    monkeypatch.setattr(ci.ensemble, "detect_content_type", lambda _aweme: "carousel")
    monkeypatch.setattr(ci, "r2_configured", lambda: False)

    async def noop_pattern(*_a: object, **_kw: object) -> None:
        return None

    import getviews_pipeline.pattern_fingerprint as pf

    monkeypatch.setattr(pf, "compute_and_upsert_pattern", noop_pattern)
    monkeypatch.setattr(ci, "_build_corpus_row", fake_build_corpus_row)

    mock_client = MagicMock()
    loop_mock = MagicMock()

    async def run_in_executor(_executor: object, fn: object, *args: object) -> object:
        assert callable(fn)
        return fn(*args)

    loop_mock.run_in_executor = AsyncMock(side_effect=run_in_executor)
    monkeypatch.setattr(ci.asyncio, "get_event_loop", lambda: loop_mock)
    monkeypatch.setattr(ci, "_upsert_rows_sync", lambda _c, _rows: None)

    pool_niche_id = 2
    await ci._ingest_candidate_awemes(
        mock_client,
        pool_niche_id,
        "Skincare",
        [nic_a, nic_b],
        niche_signal_hashtags_by_id=None,
    )
    assert captured == [5, 2]
