"""W4-1 — build_channel_findings P0 + prompt inject."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from getviews_pipeline.channel_diagnose_prompts import build_channel_diagnosis_context
from getviews_pipeline.channel_findings import (
    _cohort_er_threshold_pct,
    _in_mega_sale_window,
    build_channel_findings,
    format_distribution_from_corpus_rows,
    format_findings_for_prompt,
    optional_memo_sections_from_findings,
    synthesize_optional_section_from_findings,
)


def _video(
    *,
    views: int,
    likes: int = 0,
    comments: int = 0,
    days_ago: int = 1,
    fmt: str = "product_closeup",
) -> dict:
    return {
        "views": views,
        "likes": likes,
        "comments": comments,
        "posted_at": datetime.now(tz=UTC) - timedelta(days=days_ago),
        "content_format": fmt,
        "caption": "test",
        "duration_sec": 20,
    }


def test_finding_channel_view_ceiling_300():
    videos = [_video(views=200, likes=1, comments=0, days_ago=i) for i in range(4)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 500, "max_views": 2000},
        recent_window_30d={"avg_views": 200, "video_count": 4},
        inflection=None,
    )
    ids = [f.id for f in findings]
    assert "channel_view_ceiling_300" in ids


def test_finding_channel_format_entropy_high():
    fmts = ["a", "b", "c", "d", "e", "f", "g", "h"]
    videos = [_video(views=5000, fmt=fmts[i % len(fmts)]) for i in range(16)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 5000, "max_views": 8000},
        recent_window_30d={"avg_views": 5000, "video_count": 16},
        inflection=None,
    )
    assert any(f.id == "channel_format_entropy_high" for f in findings)


def test_finding_channel_recent_vs_peak_er_drop():
    recent = [_video(views=1000, likes=50, comments=5, days_ago=i) for i in range(3)]
    old_peak = [_video(views=8000, likes=800, comments=80, days_ago=60 + i) for i in range(3)]
    findings = build_channel_findings(
        videos=recent + old_peak,
        channel_pattern={"global_avg_views": 3000, "max_views": 8000},
        recent_window_30d={"avg_views": 1000, "video_count": 3},
        inflection={
            "peak_avg": 8000,
            "current_avg": 1000,
            "drop_pct": 87.5,
            "peak_quarter": "2025Q4",
            "current_quarter": "2026Q1",
        },
    )
    assert any(f.id == "channel_recent_vs_peak_er_drop" for f in findings)


def test_finding_channel_peer_format_saturation():
    peer_rows = [
        {"content_format": "unboxing_process", "views": 9000}
        for _ in range(8)
    ] + [{"content_format": "product_closeup", "views": 5000} for _ in range(2)]
    findings = build_channel_findings(
        videos=[_video(views=4000, fmt="unboxing_process") for _ in range(6)],
        channel_pattern={"global_avg_views": 4000, "max_views": 6000},
        recent_window_30d={"avg_views": 4000, "video_count": 6},
        inflection=None,
        peer_corpus_rows=peer_rows,
        dominant_format="unboxing_process",
    )
    assert any(f.id == "channel_peer_format_saturation" for f in findings)


def test_prompt_contains_channel_findings_block():
    videos = [_video(views=150, likes=1, comments=0, days_ago=i) for i in range(4)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 200, "max_views": 500},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
    )
    ctx = build_channel_diagnosis_context(
        handle="testchan",
        videos=videos,
        trajectory="stagnant",
        channel_pattern={"global_avg_views": 200, "max_views": 500, "formats": {}},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
        top_performers=[],
        worst_performers=[],
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks=None,
        channel_findings=findings,
    )
    assert "<<<CHANNEL FINDINGS>>>" in ctx
    assert format_findings_for_prompt(findings).startswith("<<<CHANNEL FINDINGS>>>")


def test_format_distribution_from_corpus_rows():
    rows = [
        {"content_format": "product_closeup"},
        {"content_format": "product_closeup"},
        {"content_format": "unboxing_process"},
    ]
    dist = format_distribution_from_corpus_rows(rows)
    assert dist["product_closeup"] == 67
    assert dist["unboxing_process"] == 33


def test_cohort_er_threshold_uses_p50_proxy():
    assert _cohort_er_threshold_pct({"engagement_p50": 0.04}) == pytest.approx(3.4, rel=0.01)


def test_cohort_er_threshold_default():
    assert _cohort_er_threshold_pct(None) == 2.0


def _corpus_row(
    *,
    video_id: str = "v1",
    boost: str = "organic_confident",
    content_class_id: int | None = 1,
    days_ago: int = 1,
    analysis: dict | None = None,
    caption: str = "",
) -> dict:
    return {
        "video_id": video_id,
        "boost_attribution": boost,
        "content_class_id": content_class_id,
        "posted_at": datetime.now(tz=UTC) - timedelta(days=days_ago),
        "analysis_json": analysis or {},
        "caption": caption,
    }


def test_finding_channel_compliance_aggregate():
    rows = [
        _corpus_row(
            video_id="v1",
            caption="cam kết khỏi hẳn mụn",
            analysis={"audio_transcript": "cam kết khỏi hẳn"},
        ),
        _corpus_row(video_id="v2", analysis={"promotion_type": "brand_deal"}),
        _corpus_row(video_id="v3"),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    hit = next(f for f in findings if f.id == "channel_compliance_aggregate")
    assert hit.section_hint == "policy_risk"
    assert hit.strength in ("medium", "high")


def test_finding_channel_boost_outlier_share():
    rows = [
        _corpus_row(video_id=f"v{i}", boost="suspect_medium")
        for i in range(2)
    ] + [_corpus_row(video_id="v3", boost="organic_confident")]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    hit = next(f for f in findings if f.id == "channel_boost_outlier_share")
    assert hit.section_hint == "account_health"


def test_finding_channel_persona_drift_content_class():
    rows = [
        _corpus_row(video_id="v1", content_class_id=1, days_ago=10),
        _corpus_row(video_id="v2", content_class_id=2, days_ago=8),
        _corpus_row(video_id="v3", content_class_id=3, days_ago=5),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    assert any(f.id == "channel_persona_drift" for f in findings)


def test_finding_channel_persona_drift_consistency_signals():
    rows = [
        _corpus_row(
            video_id="v1",
            analysis={
                "persona_consistency_signals": {"backdrop": "drift", "costume": "aligned"},
            },
        ),
        _corpus_row(
            video_id="v2",
            analysis={
                "persona_consistency_signals": {"speech_register": "drift"},
            },
        ),
        _corpus_row(video_id="v3"),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    assert any(f.id == "channel_persona_drift" for f in findings)


def test_finding_channel_slang_staleness():
    dated = {"slang_freshness_score": "dated", "slang_terms_used": ["flex", "slay"]}
    rows = [
        _corpus_row(video_id="v1", analysis=dated),
        _corpus_row(video_id="v2", analysis=dated),
        _corpus_row(video_id="v3", analysis={"slang_freshness_score": "fresh"}),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    hit = next(f for f in findings if f.id == "channel_slang_staleness")
    assert hit.section_hint == "what_falling"


def test_finding_channel_restricted_keyword_exposure():
    rows = [
        _corpus_row(
            video_id="v1",
            caption="cam kết khỏi hẳn mụn",
            analysis={"audio_transcript": "cam kết khỏi hẳn"},
        ),
        _corpus_row(
            video_id="v2",
            caption="100% hiệu quả",
            analysis={"audio_transcript": "100% hiệu quả"},
        ),
        _corpus_row(video_id="v3"),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    hit = next(f for f in findings if f.id == "channel_restricted_keyword_exposure")
    assert hit.section_hint == "policy_risk"


def test_finding_channel_ad_law_disclosure_gap():
    rows = [
        _corpus_row(video_id="v1", analysis={"promotion_type": "brand_deal"}),
        _corpus_row(video_id="v2", analysis={"promotion_type": "affiliate"}),
        _corpus_row(video_id="v3", analysis={"promotion_type": "organic"}),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    hit = next(f for f in findings if f.id == "channel_ad_law_disclosure_gap")
    assert hit.section_hint == "policy_risk"


def test_finding_channel_copyright_mute_risk():
    cml_bad = {
        "promotion_type": "affiliate",
        "trending_sound_profile": {"commercial_music_library_eligible": False},
    }
    rows = [
        _corpus_row(video_id="v1", analysis=cml_bad),
        _corpus_row(video_id="v2", analysis=dict(cml_bad)),
        _corpus_row(video_id="v3", analysis={"promotion_type": "organic"}),
    ]
    findings = build_channel_findings(
        videos=[],
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        handle_corpus_rows=rows,
    )
    hit = next(f for f in findings if f.id == "channel_copyright_mute_risk")
    assert hit.section_hint == "policy_risk"


def test_finding_channel_posting_cadence_vs_peer():
    videos = [_video(views=1000, days_ago=i * 10) for i in range(3)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={},
        recent_window_30d={"avg_views": 1000, "video_count": 3},
        inflection=None,
        niche_benchmarks={"posts_per_week_p50": 5.0},
    )
    hit = next(f for f in findings if f.id == "channel_posting_cadence_vs_peer")
    assert hit.section_hint == "what_falling"


def test_finding_channel_best_hour_underused():
    base = datetime.now(tz=UTC) - timedelta(days=1)
    videos = []
    for i, hour in enumerate([3, 4, 5, 6, 22, 23]):
        videos.append({
            "views": 5000 if hour >= 22 else 500,
            "likes": 50,
            "comments": 5,
            "posted_at": base.replace(hour=hour, minute=0) - timedelta(days=i),
            "content_format": "product_closeup",
            "caption": "test",
            "duration_sec": 20,
        })
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={},
        recent_window_30d={"avg_views": 2000, "video_count": 6},
        inflection=None,
    )
    assert any(f.id == "channel_best_hour_underused" for f in findings)


def test_finding_channel_mega_sale_dip(monkeypatch):
    sale_day = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "getviews_pipeline.channel_findings._now",
        lambda: sale_day,
    )
    assert _in_mega_sale_window(sale_day)

    now = sale_day
    videos = []
    for i in range(7):
        videos.append({
            "views": 200,
            "likes": 10,
            "comments": 1,
            "posted_at": now - timedelta(days=i),
            "content_format": "product_closeup",
            "caption": "test",
            "duration_sec": 20,
        })
    for i in range(7, 14):
        videos.append({
            "views": 1000,
            "likes": 10,
            "comments": 1,
            "posted_at": now - timedelta(days=i),
            "content_format": "product_closeup",
            "caption": "test",
            "duration_sec": 20,
        })
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={},
        recent_window_30d={"avg_views": 400, "video_count": 6},
        inflection=None,
    )
    assert any(f.id == "channel_mega_sale_dip" for f in findings)


def test_optional_memo_sections_from_findings():
    videos = [_video(views=150, likes=1, comments=0, days_ago=i) for i in range(4)]
    rows = [
        _corpus_row(
            video_id="v1",
            caption="cam kết khỏi hẳn",
            analysis={"audio_transcript": "cam kết khỏi hẳn"},
        ),
        _corpus_row(video_id="v2", analysis={"promotion_type": "brand_deal"}),
    ]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 200, "max_views": 500},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
        handle_corpus_rows=rows,
    )
    sections = optional_memo_sections_from_findings(findings)
    assert "account_health" in sections
    assert "policy_risk" in sections


def test_synthesize_optional_section_fallback():
    videos = [_video(views=150, likes=1, comments=0, days_ago=i) for i in range(4)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 200, "max_views": 500},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
    )
    synth = synthesize_optional_section_from_findings(
        findings, "account_health", trajectory="stagnant",
    )
    assert synth is not None
    assert synth["section_id"] == "account_health"
    assert synth["text"]


def test_prompt_includes_optional_memo_sections():
    videos = [_video(views=150, likes=1, comments=0, days_ago=i) for i in range(4)]
    findings = build_channel_findings(
        videos=videos,
        channel_pattern={"global_avg_views": 200, "max_views": 500},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
    )
    optional = optional_memo_sections_from_findings(findings)
    ctx = build_channel_diagnosis_context(
        handle="testchan",
        videos=videos,
        trajectory="stagnant",
        channel_pattern={"global_avg_views": 200, "max_views": 500, "formats": {}},
        recent_window_30d={"avg_views": 150, "video_count": 4},
        inflection=None,
        top_performers=[],
        worst_performers=[],
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks=None,
        channel_findings=findings,
        optional_memo_sections=optional,
    )
    assert "<<<OPTIONAL MEMO SECTIONS>>>" in ctx
    assert "account_health" in ctx
