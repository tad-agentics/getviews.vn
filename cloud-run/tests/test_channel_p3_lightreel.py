"""P3 (Lightreel audit 2026-06-11) — recent-content feature audit + brand UGC axis.

G4: ``compute_recent_content_audit`` aggregates frame-level features (face /
hook / overlay / audio role) across the handle's already-analysed corpus rows
— zero new Gemini calls — and the context builder injects them as
``<<<RECENT CONTENT AUDIT>>>`` for evidence-backed what_falling bullets.

G5: ``fetch_brand_ugc_videos`` finds external creators posting ABOUT the
brand via one ED keyword search (flag-gated by BRAND_UGC_SEARCH_ENABLED,
default OFF) and feeds the new ``ugc_vs_channel`` memo section.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from getviews_pipeline.channel_diagnose import (
    _audit_features_from_analysis,
    _brand_term_from_handle,
    compute_recent_content_audit,
    fetch_brand_ugc_videos,
)

# ── G4: feature extraction per video ─────────────────────────────────


def test_audit_features_face_hook_overlay_role() -> None:
    analysis = {
        "scenes": [
            {"type": "product_shot", "subject": "product", "overlay_style": "none"},
            {"type": "face_to_camera", "subject": "face", "overlay_style": "bold_center"},
        ],
        "hook_analysis": {"hook_phrase": "Bạn có biết vì sao", "hook_type": "question"},
        "audio_track_role": "trending_sound",
    }
    f = _audit_features_from_analysis(analysis)
    assert f == {
        "has_face": True,
        "has_overlay": True,
        "has_hook": True,
        "audio_track_role": "trending_sound",
    }


def test_audit_features_absences_and_normalised_keys() -> None:
    # Normalised payloads use scene_type instead of type — both must count.
    analysis = {
        "scenes": [{"scene_type": "face_to_camera"}],
        "hook_analysis": {"hook_phrase": "", "hook_type": "none"},
    }
    f = _audit_features_from_analysis(analysis)
    assert f is not None
    assert f["has_face"] is True
    assert f["has_hook"] is False
    assert f["audio_track_role"] is None
    assert _audit_features_from_analysis({}) is None
    assert _audit_features_from_analysis(None) is None


def _row(views: int, *, face: bool, hook: bool = True, role: str = "trending_sound") -> dict:
    return {
        "views": views,
        "analysis_json": {
            "scenes": [{"subject": "face" if face else "product"}],
            "hook_analysis": {"hook_phrase": "Câu hook mở đầu" if hook else ""},
            "audio_track_role": role,
        },
    }


def test_compute_audit_counts_and_face_views_contrast() -> None:
    rows = [
        _row(500_000, face=True),
        _row(300_000, face=True),
        _row(20_000, face=False, hook=False, role="silent"),
        _row(10_000, face=False, hook=False, role="silent"),
        {"views": 99, "analysis_json": None},  # no extraction → skipped
    ]
    audit = compute_recent_content_audit(rows, recent_total=8)
    assert audit is not None
    assert audit["videos_scanned"] == 4
    assert audit["recent_total"] == 8
    assert audit["face_videos"] == 2
    assert audit["hook_videos"] == 2
    assert audit["audio_roles"] == {"trending_sound": 2, "silent": 2}
    # The killer stat: avg views with vs without a human face.
    assert audit["avg_views_with_face"] == 400_000
    assert audit["avg_views_without_face"] == 15_000


def test_compute_audit_none_when_thin() -> None:
    rows = [_row(1000, face=True), _row(2000, face=False)]
    assert compute_recent_content_audit(rows) is None
    assert compute_recent_content_audit([]) is None


# ── G5: brand term + UGC fetch ───────────────────────────────────────


def test_brand_term_strips_noise_tokens() -> None:
    assert _brand_term_from_handle("curnon.official") == "curnon"
    assert _brand_term_from_handle("coolmate_vn") == "coolmate"
    assert _brand_term_from_handle("shopdecor88") == "shopdecor"
    # All-noise handles fall back to the raw handle.
    assert _brand_term_from_handle("vn.official") == "vn.official"


def _aweme(uid: str, views: int, desc: str, followers: int = 25_000) -> dict[str, Any]:
    return {
        "aweme_id": f"aw-{uid}-{views}",
        "desc": desc,
        "statistics": {"play_count": views, "digg_count": 10, "comment_count": 2},
        "author": {"unique_id": uid, "follower_count": followers},
        "video": {"cover": {"url_list": ["https://cdn/x.jpg"]}},
    }


@pytest.mark.asyncio
async def test_fetch_brand_ugc_filters_and_ranks() -> None:
    awemes = [
        _aweme("havan29", 1_600_000, "Review đồng hồ curnon sau 1 tháng"),
        _aweme("havan29", 33_000, "curnon thường ngày"),  # same author, lower → dropped
        _aweme("curnon.official", 9_000_000, "curnon sale"),  # own channel → excluded
        _aweme("randomgirl", 800_000, "outfit hôm nay"),  # no brand mention → excluded
        _aweme("smallfan", 10_000, "yêu curnon"),  # below 1.5× floor → excluded
        _aweme("nangtho.style_", 545_000, "Phối đồ với curnon mesa"),
    ]
    with patch(
        "getviews_pipeline.channel_diagnose.ensemble.fetch_keyword_search",
        return_value=(awemes, None),
    ):
        out = await fetch_brand_ugc_videos("curnon.official", recent_avg_views=20_000)
    assert [c["handle"] for c in out] == ["havan29", "nangtho.style_"]
    assert out[0]["views"] == 1_600_000
    assert out[0]["multiplier"] == 80.0
    assert out[0]["caption_snippet"].startswith("Review đồng hồ curnon")
    assert out[0]["followers"] == 25_000


@pytest.mark.asyncio
async def test_fetch_brand_ugc_graceful_on_search_failure() -> None:
    with patch(
        "getviews_pipeline.channel_diagnose.ensemble.fetch_keyword_search",
        side_effect=RuntimeError("ED down"),
    ):
        assert await fetch_brand_ugc_videos("curnon.official", 20_000) == []


# ── Context blocks + section plumbing ────────────────────────────────


def _build_ctx(**overrides: Any) -> str:
    from getviews_pipeline.channel_diagnose_prompts import build_channel_diagnosis_context

    kwargs: dict[str, Any] = dict(
        handle="testcreator",
        videos=[],
        trajectory="decline_from_peak",
        channel_pattern={},
        recent_window_30d={},
        inflection=None,
        top_performers=[],
        worst_performers=[],
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks=None,
    )
    kwargs.update(overrides)
    return build_channel_diagnosis_context(**kwargs)


def test_context_audit_block_rendered_and_omitted() -> None:
    audit = {
        "videos_scanned": 6,
        "recent_total": 9,
        "face_videos": 1,
        "hook_videos": 2,
        "overlay_videos": 3,
        "audio_roles": {"silent": 4, "trending_sound": 2},
        "avg_views_with_face": 400_000,
        "avg_views_without_face": 15_000,
    }
    ctx = _build_ctx(recent_content_audit=audit)
    assert "<<<RECENT CONTENT AUDIT" in ctx
    assert "has_human_face: 1/6" in ctx
    assert "silent=4" in ctx
    assert "avg_views_with_face: 400K" in ctx
    assert "<<<RECENT CONTENT AUDIT" not in _build_ctx(recent_content_audit=None)


def test_context_brand_ugc_block_rendered_and_omitted() -> None:
    creators = [{
        "handle": "havan29",
        "followers": 12_300,
        "views": 1_600_000,
        "caption_snippet": "Review đồng hồ curnon",
        "multiplier": 80.0,
    }]
    ctx = _build_ctx(brand_ugc_creators=creators)
    assert "<<<UGC CREATORS" in ctx
    assert "@havan29" in ctx
    assert "gấp 80.0× TB 30 ngày của kênh" in ctx
    assert "<<<UGC CREATORS" not in _build_ctx(brand_ugc_creators=None)


def test_system_prompt_has_ugc_section_and_audit_rule() -> None:
    from getviews_pipeline.channel_diagnose_prompts import CHANNEL_DIAGNOSIS_SYSTEM_PROMPT

    assert "=== ugc_vs_channel ===" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    assert "<<<RECENT CONTENT AUDIT>>>" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    assert "không suy đoán" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT


def test_default_title_ugc_vs_channel() -> None:
    from getviews_pipeline.channel_diagnose_prompts import get_default_title

    for traj in ("decline_from_peak", "breakout", "new_account"):
        assert get_default_title("ugc_vs_channel", traj) == "UGC VS KÊNH CHÍNH"


def test_section_header_regex_parses_ugc_vs_channel() -> None:
    from getviews_pipeline.routers.video import _parse_sections_from_narrative

    narrative = (
        "=== verdict ===\nTITLE: BỨC TRANH TỔNG THỂ\nNội dung.\n\n"
        "=== ugc_vs_channel ===\nTITLE: UGC VS KÊNH CHÍNH\n@havan29 đạt 1.6M.\n\n"
        "=== recommendations ===\nTITLE: KẾ HOẠCH HÀNH ĐỘNG\n1. **Làm X**\nVì Y.\n"
    )
    sections = _parse_sections_from_narrative(narrative, "decline_from_peak")
    by_id = {s["section_id"]: s for s in sections}
    assert "ugc_vs_channel" in by_id
    assert by_id["ugc_vs_channel"]["title"] == "UGC VS KÊNH CHÍNH"
    assert "@havan29" in by_id["ugc_vs_channel"]["text"]


def test_sections_to_emit_includes_ugc_only_when_brand_ugc() -> None:
    from getviews_pipeline.channel_findings import select_channel_sections_to_emit

    base_kwargs: dict[str, Any] = dict(findings=[], trajectory="decline_from_peak")
    with_ugc = select_channel_sections_to_emit(**base_kwargs, has_brand_ugc=True)
    without = select_channel_sections_to_emit(**base_kwargs)
    assert "ugc_vs_channel" in with_ugc
    assert "ugc_vs_channel" not in without
    # Ordering: after competitive_landscape, before recommendations.
    assert with_ugc.index("ugc_vs_channel") > with_ugc.index("competitive_landscape")
    assert with_ugc.index("ugc_vs_channel") < with_ugc.index("recommendations")


def test_brand_ugc_flag_default_off() -> None:
    from getviews_pipeline import config

    assert config.BRAND_UGC_SEARCH_ENABLED is False


# ── P3 follow-up: audit inside video_diagnosis channel context ────────


def test_channel_context_sync_attaches_audit() -> None:
    from unittest.mock import MagicMock

    from getviews_pipeline.pipelines import fetch_channel_context_sync

    rows = [
        {**_row(500_000, face=True), "video_id": f"v{i}", "caption": "c",
         "content_format": "talking_head", "posted_at": "2026-06-01"}
        for i in range(2)
    ] + [
        {**_row(20_000, face=False, hook=False, role="silent"), "video_id": f"w{i}",
         "caption": "c", "content_format": "product_shot", "posted_at": "2026-05-20"}
        for i in range(2)
    ]
    client = MagicMock()
    (client.table.return_value.select.return_value.eq.return_value
     .neq.return_value.order.return_value.limit.return_value
     .execute.return_value) = type("R", (), {"data": rows})()
    with patch("getviews_pipeline.pipelines.get_service_client", return_value=client), patch(
        "getviews_pipeline.pipelines._dominant_creator_persona_from_corpus",
        return_value=None,
    ):
        ctx = fetch_channel_context_sync("creator", "current-vid")
    assert ctx["available"] is True
    audit = ctx.get("recent_content_audit")
    assert audit is not None
    assert audit["videos_scanned"] == 4
    assert audit["face_videos"] == 2


def test_trim_channel_context_passes_audit_through() -> None:
    from getviews_pipeline.diagnose_prompts import _trim_channel_context

    audit = {"videos_scanned": 5, "face_videos": 1, "hook_videos": 2,
             "overlay_videos": 3, "audio_roles": {"silent": 4}}
    trimmed = _trim_channel_context({
        "available": True, "sample_size": 5, "median_views": 1000,
        "recent_content_audit": audit,
    })
    assert trimmed["recent_content_audit"] == audit
    # Absent → key absent (no empty-dict noise in the prompt payload).
    trimmed_no = _trim_channel_context({"available": True, "sample_size": 5})
    assert "recent_content_audit" not in trimmed_no


def test_v6_rules_allow_audit_citation_in_channel_pattern() -> None:
    from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION

    assert "recent_content_audit" in DIAGNOSIS_V6_JSON_INSTRUCTION
    assert "KHÔNG suy đoán ngoài số đếm" in DIAGNOSIS_V6_JSON_INSTRUCTION
