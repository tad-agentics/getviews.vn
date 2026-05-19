"""Reference selection for finalize / answer video synthesis."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from getviews_pipeline.pipelines import REF_N
from getviews_pipeline.services.references import select_synthesis_references_for_video


def _corpus_pick(aid: str) -> dict:
    return {
        "aweme_id": aid,
        "_from_corpus": True,
        "_corpus_analysis": {"hook_analysis": {"hook_type": "question"}},
        "statistics": {"play_count": 10_000},
        "author": {"unique_id": "peer"},
    }


@pytest.mark.asyncio
async def test_partial_corpus_picks_kept_when_below_ref_n(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thin niche pool must not discard 1–(REF_N-1) corpus refs and go live-only."""
    one = _corpus_pick("111")

    async def _pool(*_a: object, **_k: object) -> list[dict]:
        return [one]

    monkeypatch.setattr(
        "getviews_pipeline.corpus_context.fetch_corpus_reference_pool",
        _pool,
    )
    monkeypatch.setattr(
        "getviews_pipeline.services.references._select_by_proximity_then_er",
        lambda pool, **kwargs: list(pool)[: kwargs.get("n", REF_N)],
    )
    monkeypatch.setattr(
        "getviews_pipeline.services.references._maybe_merge_content_targeted_refs_async",
        AsyncMock(side_effect=lambda pool, picks, **kwargs: (pool, picks)),
    )
    monkeypatch.setattr(
        "getviews_pipeline.services.references._niche_aweme_pool",
        AsyncMock(return_value=[]),
    )

    live_called = False

    async def _live(_niche: str, _vid: str) -> tuple[list, list]:
        nonlocal live_called
        live_called = True
        return [], []

    syn, slim, _block = await select_synthesis_references_for_video(
        niche_name="Thời trang",
        video_id="999",
        video_desc="review nhẫn",
        video_hashtags=["thoitrang"],
        live_search_fn=_live,
    )

    assert len(syn) == 1
    assert syn[0]["aweme_id"] == "111"
    assert len(slim) == 1
    assert live_called is True  # supplements when still under REF_N


@pytest.mark.asyncio
async def test_live_supplements_corpus_without_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    one = _corpus_pick("111")

    async def _pool(*_a: object, **_k: object) -> list[dict]:
        return [one]

    monkeypatch.setattr(
        "getviews_pipeline.corpus_context.fetch_corpus_reference_pool",
        _pool,
    )
    monkeypatch.setattr(
        "getviews_pipeline.services.references._select_by_proximity_then_er",
        lambda pool, **kwargs: list(pool)[: kwargs.get("n", REF_N)],
    )
    monkeypatch.setattr(
        "getviews_pipeline.services.references._maybe_merge_content_targeted_refs_async",
        AsyncMock(side_effect=lambda pool, picks, **kwargs: (pool, picks)),
    )
    monkeypatch.setattr(
        "getviews_pipeline.services.references._niche_aweme_pool",
        AsyncMock(return_value=[]),
    )

    async def _live(_niche: str, _vid: str) -> tuple[list, list]:
        return (
            [
                {"aweme_id": "111", "analysis": {}},
                {"aweme_id": "222", "analysis": {}},
            ],
            [{"aweme_id": "111"}, {"aweme_id": "222"}],
        )

    syn, slim, _ = await select_synthesis_references_for_video(
        niche_name="Thời trang",
        video_id="999",
        video_desc="review",
        video_hashtags=[],
        live_search_fn=_live,
    )

    aids = [str(r.get("aweme_id")) for r in syn]
    assert aids == ["111", "222"]
    assert len(slim) == 2
