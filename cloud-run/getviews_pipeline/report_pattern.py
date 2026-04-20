"""Phase C.2 — Pattern report aggregator (fixture + live pipeline hook)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.report_types import (
    ActionCardPayload,
    ConfidenceStrip,
    ContrastAgainst,
    EvidenceCardPayload,
    HookFinding,
    Lifecycle,
    Metric,
    PatternCellPayload,
    PatternPayload,
    SourceRow,
    SumStat,
    WoWDiff,
)


def _metric(val: str, num: float, definition: str) -> Metric:
    return Metric(value=val, numeric=num, definition=definition)


def build_fixture_pattern_report() -> dict[str, Any]:
    """C.1 fixture — validates as PatternPayload; WhatStalled invariant: empty + reason."""
    confidence = ConfidenceStrip(
        sample_size=47,
        window_days=7,
        niche_scope="Tech",
        freshness_hours=3,
        intent_confidence="high",
        what_stalled_reason="stub: corpus slice empty for negative quartile",
    )
    lf = Lifecycle(first_seen="2026-01-01", peak="2026-03-15", momentum="rising")
    hf = HookFinding(
        rank=1,
        pattern="Mình vừa test ___ và",
        retention=_metric("74%", 0.74, "viewers past 15s"),
        delta=_metric("+312%", 3.12, "vs niche avg"),
        uses=214,
        lifecycle=lf,
        contrast_against=ContrastAgainst(pattern="Before/after swipe", why_this_won="Opens with curiosity gap"),
        prerequisites=["Face visible 0–1s", "On-screen text"],
        insight="Strong hook retention vs niche baseline.",
        evidence_video_ids=[],
    )
    ev = EvidenceCardPayload(
        video_id="stub-1",
        creator_handle="@demo",
        title="Stub video",
        views=412000,
        retention=0.78,
        duration_sec=28,
        bg_color="#1F2A3B",
        hook_family="testimonial",
    )
    payload = PatternPayload(
        confidence=confidence,
        wow_diff=WoWDiff(),
        tldr={
            "thesis": "Hook-first testimonials are winning in Tech this week.",
            "callouts": [
                SumStat(label="Videos scanned", value="47", trend="+12%", tone="up"),
                SumStat(label="Median retention", value="72%", trend="+4%", tone="up"),
                SumStat(label="Creators", value="18", trend="flat", tone="neutral"),
            ],
        },
        findings=[hf, hf.model_copy(update={"rank": 2, "pattern": "POV ___"}), hf.model_copy(update={"rank": 3, "pattern": "Listicle 3 điều"})],
        what_stalled=[],
        evidence_videos=[ev] * 6,
        patterns=[
            PatternCellPayload(title="Duration", finding="28s", detail="Mode band", chart_kind="duration", chart_data={}),
            PatternCellPayload(title="Hook timing", finding="0.4s", detail="Median", chart_kind="hook_timing", chart_data={}),
            PatternCellPayload(title="Sound", finding="60% orig", detail="Mix", chart_kind="sound_mix", chart_data={}),
            PatternCellPayload(title="CTA", finding="Follow", detail="Family", chart_kind="cta_bars", chart_data={}),
        ],
        actions=[
            ActionCardPayload(icon="sparkles", title="Mở Xưởng Viết", sub="Draft từ hook #1", cta="Mở", primary=True, forecast={"expected_range": "8K–15K", "baseline": "6.2K"}),
            ActionCardPayload(icon="search", title="Soi kênh đối thủ", sub="Benchmark retention", cta="Mở", forecast={"expected_range": "—", "baseline": "—"}),
            ActionCardPayload(icon="calendar", title="Theo dõi trend", sub="Tuần này", cta="Xem", forecast={"expected_range": "—", "baseline": "—"}),
        ],
        sources=[
            SourceRow(kind="video", label="Corpus", count=47, sub="Tech · 7d"),
        ],
        related_questions=["Hook nào đang giảm?", "Format nào oversaturated?", "Niche con nào đang nổi?"],
    )
    return payload.model_dump()


def build_pattern_report(_niche_id: int, _query: str, _intent_type: str, window_days: int = 7) -> dict[str, Any]:
    """C.2 entry — fixture until aggregators wire to DB; ``window_days`` from C.0.3 adaptive."""
    data = build_fixture_pattern_report()
    conf = data.get("confidence")
    if isinstance(conf, dict):
        conf["window_days"] = window_days
    if isinstance(data.get("sources"), list) and data["sources"]:
        s0 = data["sources"][0]
        if isinstance(s0, dict) and "sub" in s0:
            scope = conf.get("niche_scope", "Tech") if isinstance(conf, dict) else "Tech"
            s0["sub"] = f"{scope} · {window_days}d"
    return data
