"""Reference pool proximity backfill for live_search slim cards."""

from __future__ import annotations

from getviews_pipeline.services.references import (
    _ensure_slim_refs_proximity_scores,
    _proximity_score_for_ref,
)


def test_proximity_score_for_analyze_aweme_synthesis_ref() -> None:
    ref = {
        "aweme_id": "999",
        "metadata": {
            "video_id": "999",
            "description": "đồng hồ nam cao cấp review chi tiết",
        },
        "analysis": {"audio_transcript": ""},
    }
    score = _proximity_score_for_ref(
        ref,
        video_desc="Review đồng hồ nam mới",
        video_hashtags=["#dongho"],
    )
    assert score >= 1


def test_ensure_slim_refs_backfills_live_search_without_corpus_score() -> None:
    synthesis = [
        {
            "aweme_id": "888",
            "metadata": {"video_id": "888", "description": "skincare routine da dầu"},
            "analysis": {},
        }
    ]
    slim = [
        {
            "aweme_id": "888",
            "desc": "skincare routine da dầu",
            "thumbnail_url": "https://thumb/888.jpg",
            "tiktok_url": "https://tiktok.com/@x/video/888",
            "source": "live_search",
        }
    ]
    _ensure_slim_refs_proximity_scores(
        synthesis,
        slim,
        video_desc="Routine skincare cho da dầu",
        video_hashtags=["#skincare"],
    )
    assert int(slim[0].get("content_proximity_score") or 0) >= 1


def test_ensure_slim_refs_does_not_overwrite_corpus_score() -> None:
    slim = [{"aweme_id": "111", "content_proximity_score": 5}]
    _ensure_slim_refs_proximity_scores(
        [{"aweme_id": "111", "metadata": {"description": "other"}}],
        slim,
        video_desc="x",
        video_hashtags=[],
    )
    assert slim[0]["content_proximity_score"] == 5
