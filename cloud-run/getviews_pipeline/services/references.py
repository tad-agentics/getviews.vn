"""Reference-video selection for synthesis (stream + finalize parity)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from getviews_pipeline.pipelines import (  # noqa: E402
    REF_N,
    _maybe_merge_content_targeted_refs_async,
    _niche_aweme_pool,
    _reference_evidence_lines,
    _select_by_proximity_then_er,
    _slim_reference_video,
)

__all__ = [
    "REF_N",
    "corpus_aweme_to_synthesis_ref",
    "select_synthesis_references_for_video",
    "_slim_reference_video",
]


def corpus_aweme_to_synthesis_ref(aweme: dict[str, Any]) -> dict[str, Any]:
    """Shape a corpus pool aweme like ``run_video_diagnosis`` analyzed refs."""
    from getviews_pipeline.output_redesign import hook_type_vi

    stats = aweme.get("statistics") or {}
    views = int(stats.get("play_count") or 0)
    handle = (aweme.get("author") or {}).get("unique_id") or ""
    corpus_analysis = aweme.get("_corpus_analysis") or {}
    raw_hook_type = (corpus_analysis.get("hook_analysis") or {}).get("hook_type") or ""
    return {
        "aweme_id": aweme["aweme_id"],
        "analysis": corpus_analysis,
        "metadata": {
            "video_id": aweme["aweme_id"],
            "author": {"username": handle},
            "views": views,
            "tiktok_url": aweme.get("_corpus_tiktok_url", ""),
            "thumbnail_url": aweme.get("thumbnail_url"),
            "days_ago": aweme.get("_corpus_days_ago", 0),
            "breakout": aweme.get("_corpus_breakout", 0.0),
            "hook_type": raw_hook_type,
            "hook_type_vi": hook_type_vi(raw_hook_type),
            "content_type": aweme.get("_corpus_content_type", "video"),
        },
    }


async def select_synthesis_references_for_video(
    *,
    niche_name: str,
    video_id: str,
    video_desc: str,
    video_hashtags: list[str],
    preferred_content_format: str | None = None,
    live_search_fn: Any | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Corpus pool → proximity picks → content-targeted merge → evidence block.

    ``live_search_fn`` — optional ``async (niche_name, video_id) -> (synthesis, slim)``
    for Ensemble fallback when corpus is sparse (wired from ``video_analyze``).
    """
    from getviews_pipeline.corpus_context import fetch_corpus_reference_pool

    niche = niche_name.strip()
    target_id = video_id.strip()
    if not niche or not target_id:
        return [], [], ""

    corpus_pool = await fetch_corpus_reference_pool(
        niche, days=30, limit=40, exclude_video_id=target_id
    )
    for v in corpus_pool:
        v["niche_label"] = niche

    pref = str(preferred_content_format or "").strip().lower()
    if pref:
        corpus_pool.sort(
            key=lambda v: (
                0 if str(v.get("_corpus_content_format") or "").strip().lower() == pref else 1,
                -float(v.get("_corpus_er") or 0.0),
            ),
        )
    else:
        corpus_pool.sort(key=lambda v: -float(v.get("_corpus_er") or 0.0))

    cached_ids = {target_id}
    corpus_source = "corpus"
    pool = list(corpus_pool)
    picks: list[dict[str, Any]] = []

    if len(corpus_pool) >= REF_N:
        picks = _select_by_proximity_then_er(
            corpus_pool,
            video_desc=video_desc,
            video_hashtags=video_hashtags,
            cached_ids=cached_ids,
            n=REF_N,
            recency_days=30,
        )
    else:
        corpus_source = "live_search" if len(corpus_pool) == 0 else "sparse_fallback"
        live_pool = await _niche_aweme_pool(niche, period=30)
        for v in live_pool:
            v.setdefault("niche_label", niche)
        pool = corpus_pool + [v for v in live_pool if v.get("aweme_id") not in cached_ids]
        picks = _select_by_proximity_then_er(
            pool,
            video_desc=video_desc,
            video_hashtags=video_hashtags,
            cached_ids=cached_ids,
            n=REF_N,
            recency_days=30,
        )

    pool, picks = await _maybe_merge_content_targeted_refs_async(
        pool,
        picks,
        video_desc=video_desc,
        video_hashtags=video_hashtags,
        niche=niche,
        cached_ids=cached_ids,
        n=REF_N,
        recency_days=30,
    )

    synthesis_refs: list[dict[str, Any]] = []
    slim_refs: list[dict[str, Any]] = []

    corpus_picks = [p for p in picks if p.get("_from_corpus")][:REF_N]
    if len(corpus_picks) >= REF_N:
        synthesis_refs = [corpus_aweme_to_synthesis_ref(p) for p in corpus_picks]
        slim_refs = [_slim_reference_video(p, "corpus") for p in corpus_picks]
    elif live_search_fn is not None:
        try:
            live_syn, live_slim = await live_search_fn(niche, target_id)
            if live_syn:
                synthesis_refs = live_syn
                slim_refs = live_slim
                corpus_source = "live_search"
        except Exception as exc:
            logger.warning("[references] live_search_fn failed: %s", exc)

    evidence_block = _reference_evidence_lines(synthesis_refs, corpus_source)
    return synthesis_refs, slim_refs, evidence_block
