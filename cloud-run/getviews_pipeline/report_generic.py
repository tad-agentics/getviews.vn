"""Phase C.5 — Generic humility report (stub)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.report_types import ConfidenceStrip, EvidenceCardPayload, GenericPayload, SourceRow


def build_generic_report(_niche_id: int | None, query: str) -> dict[str, Any]:
    conf = ConfidenceStrip(
        sample_size=12,
        window_days=7,
        niche_scope=None,
        freshness_hours=24,
        intent_confidence="low",
    )
    ev = EvidenceCardPayload(
        video_id="g1",
        creator_handle="@x",
        title="Stub",
        views=1000,
        retention=0.5,
        duration_sec=20,
        bg_color="#222",
        hook_family="talking_head",
    )
    payload = GenericPayload(
        confidence=conf,
        off_taxonomy={
            "suggestions": [
                {"label": "Soi kênh", "route": "/app/channel", "icon": "eye"},
                {"label": "Xưởng viết", "route": "/app/script", "icon": "film"},
                {"label": "Tìm KOL", "route": "/app/kol", "icon": "users"},
            ]
        },
        narrative={"paragraphs": [f"Bạn hỏi: «{query[:120]}». Đây là gợi ý ngắn dựa trên corpus rộng — hãy thử các công cụ bên dưới."]},
        evidence_videos=[ev, ev, ev],
        sources=[SourceRow(kind="datapoint", label="Corpus", count=12, sub="broad")],
        related_questions=["Thử hỏi theo niche cụ thể?"],
    )
    return payload.model_dump()

