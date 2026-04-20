"""Phase C.4 — Timing report (stub)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.report_types import ActionCardPayload, ConfidenceStrip, SourceRow, TimingPayload


def build_timing_report(niche_id: int, query: str, window_days: int = 7) -> dict[str, Any]:
    grid = [[0.1 * ((i + j) % 10) for j in range(8)] for i in range(7)]
    payload = TimingPayload(
        confidence=ConfidenceStrip(
            sample_size=80,
            window_days=window_days,
            niche_scope="Tech",
            freshness_hours=1,
            intent_confidence="high",
        ),
        top_window={"day": "Thứ 7", "hours": "18:00 – 22:00", "lift_multiplier": 2.2},
        top_3_windows=[
            {"rank": 1, "day": "Thứ 7", "hours": "18–22", "lift_multiplier": 2.2},
            {"rank": 2, "day": "Chủ nhật", "hours": "10–14", "lift_multiplier": 1.8},
            {"rank": 3, "day": "Thứ 6", "hours": "20–23", "lift_multiplier": 1.5},
        ],
        lowest_window={"day": "Thứ 3", "hours": "3–6h sáng"},
        grid=grid,
        variance_note={"kind": "strong", "label": "Heatmap có ý nghĩa"},
        fatigue_band=None,
        actions=[
            ActionCardPayload(icon="calendar", title="Lên lịch", sub="Cửa sổ mạnh nhất", cta="Copy", primary=True, forecast={"expected_range": "—", "baseline": "—"}),
            ActionCardPayload(icon="users", title="Đối thủ", sub="Ai đang post khung này", cta="Xem", forecast={"expected_range": "—", "baseline": "—"}),
        ],
        sources=[SourceRow(kind="video", label="Mẫu", count=80, sub=f"{window_days}d")],
        related_questions=["Đổi khung giờ theo ngách con?"],
    )
    return payload.model_dump()

