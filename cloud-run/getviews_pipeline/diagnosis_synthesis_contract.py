"""Typed kwargs contract for ``synthesize_diagnosis_v2`` call sites.

Both single-video (``finalize_video_narrative_layer``) and compare
(``run_video_diagnosis``) must build synthesis kwargs through
``diagnosis_synthesis_kwargs``. Every parameter is required (no defaults)
so omitting a new engine param fails at compile time and at runtime.

See ``tests/test_diagnosis_synthesis_contract.py`` for signature parity.
"""

from __future__ import annotations

from typing import Any


def diagnosis_synthesis_kwargs(
    *,
    content_format: str,
    niche_name: str,
    corpus_size: int,
    niche_meta: dict[str, Any],
    reference_videos: list[dict[str, Any]],
    user_analysis: dict[str, Any],
    user_stats: dict[str, Any],
    collapsed_questions: list[str] | None,
    wants_directions: bool,
    layer0_context: str,
    corpus_citation: str,
    persona_block: str,
    performance_tier: str,
    channel_context: dict[str, Any] | None,
    errors: list[dict[str, Any]] | None,
    reference_evidence_block: str,
    creator_format_history_block: str,
    cross_format_signal: dict[str, Any] | None,
    niche_posting_context_block: str,
    comment_radar: dict[str, Any] | None,
    hook_effectiveness: list[dict[str, Any]] | None,
    addressing_mode: str,
    video_creator_handle: str | None,
) -> dict[str, Any]:
    """Collect synthesis kwargs; no fetching or resolution."""
    return {
        "content_format": content_format,
        "niche_name": niche_name,
        "corpus_size": corpus_size,
        "niche_meta": niche_meta,
        "reference_videos": reference_videos,
        "user_analysis": user_analysis,
        "user_stats": user_stats,
        "collapsed_questions": collapsed_questions,
        "wants_directions": wants_directions,
        "layer0_context": layer0_context,
        "corpus_citation": corpus_citation,
        "persona_block": persona_block,
        "performance_tier": performance_tier,
        "channel_context": channel_context,
        "errors": errors,
        "reference_evidence_block": reference_evidence_block,
        "creator_format_history_block": creator_format_history_block,
        "cross_format_signal": cross_format_signal,
        "niche_posting_context_block": niche_posting_context_block,
        "comment_radar": comment_radar,
        "hook_effectiveness": hook_effectiveness,
        "addressing_mode": addressing_mode,
        "video_creator_handle": video_creator_handle,
    }


__all__ = ["diagnosis_synthesis_kwargs"]
