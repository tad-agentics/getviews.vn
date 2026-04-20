"""Phase C.3 — Ideas report (stub)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.report_types import ActionCardPayload, ConfidenceStrip, IdeasPayload, IdeaBlockPayload, SourceRow


def build_ideas_report(
    niche_id: int,
    query: str,
    intent_type: str,
    window_days: int = 7,
    variant: str = "standard",
) -> dict[str, Any]:
    conf = ConfidenceStrip(
        sample_size=60,
        window_days=window_days,
        niche_scope="Tech",
        freshness_hours=2,
        intent_confidence="medium",
    )
    block = IdeaBlockPayload(
        id="1",
        title="Stub idea",
        tag="tutorial",
        angle="Quick demo with proof",
        why_works="High completion in corpus.",
        evidence_video_ids=[],
        hook="POV: bạn vừa phát hiện…",
        slides=[{"step": i, "body": f"Slide {i}"} for i in range(1, 7)],
        metric={"label": "RETENTION DỰ KIẾN", "value": "72%", "range": "64–80%"},
        prerequisites=[],
        confidence={"sample_size": 12, "creators": 5},
        style="handheld",
    )
    payload = IdeasPayload(
        confidence=conf,
        lead="Dựa trên corpus, đây là 5 hướng đang giữ retention.",
        ideas=[block] * 5,
        style_cards=[{"id": str(i), "name": f"Style {i}", "desc": "stub", "paired_ideas": ["#1"]} for i in range(5)],
        stop_doing=[{"bad": "x", "why": "y", "fix": "z"}] * 5,
        actions=[
            ActionCardPayload(icon="sparkles", title="Mở script", sub="Ý #1", cta="Mở", primary=True, forecast={"expected_range": "—", "baseline": "—"}),
            ActionCardPayload(icon="save", title="Lưu template", sub="5 ý", cta="Lưu", forecast={"expected_range": "—", "baseline": "—"}),
        ],
        sources=[SourceRow(kind="video", label="Corpus", count=60, sub="7d")],
        related_questions=["Thêm ý cho hook khác?"],
        variant="hook_variants" if variant == "hook_variants" else "standard",
    )
    return payload.model_dump()

