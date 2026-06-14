"""Unit tests for diagnosis section pool + v6 narrative envelope helpers."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.diagnosis_quality import (
    diagnosis_v6_word_budget_exceeded,
    score_diagnosis_output_v6,
)
from getviews_pipeline.gemini import (
    _clamp_finding_evidence_refs,
    _v6_section_body_and_narrative,
)
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def test_select_sections_minimal_ctx() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={"promotion_type": "organic"},
        user_stats={"caption": "hi", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "diagnosis" in out
    assert "next_video" not in out


def test_select_sections_includes_commerce_when_organic_but_commercial_intent_signals() -> None:
    """Regression: organic promo + shop_direct intent yields commerce signals — section must emit."""
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "commerce_intent": {
                "conversion_objective": "shop_direct",
                "product_price_tier": "not_commerce",
                "creator_type": "kos_seller",
                "verbal_cta_present": True,
                "disclosure_present": True,
                "disclosure_form": "voice",
            },
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "question",
                "hook_notes": "",
                "hook_timeline": [],
            },
        },
        user_stats={"caption": "hi", "views": 50_000, "commerce_conversion": {"order_count": 80}},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    assert manifest.get("commerce"), "expected commerce signals (intent + optional §12 override)"
    out = select_sections_to_emit(manifest, ctx)
    assert "commerce" in out


def test_select_sections_includes_hook_analysis_after_compliance_when_salient() -> None:
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "affiliate_shopee",
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "question",
                "hook_notes": "",
                "hook_timeline": [],
                "hook_layering": "single",
            },
        },
        user_stats={"caption": "hi", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
    )
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "hook_analysis" in out
    assert out.index("diagnosis") < out.index("hook_analysis")
    assert "commerce" in out
    assert out.index("hook_analysis") < out.index("commerce")


def test_select_sections_includes_hook_analysis_when_vision_hook_present() -> None:
    """Basic depth still synthesizes hook prose when extraction populated hook_analysis."""
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "hook_analysis": {
                "first_frame_type": "face",
                "hook_phrase": "x",
                "hook_type": "dialect_identity",
                "hook_notes": "",
                "hook_timeline": [],
                "dialect_detected": "none",
            },
        },
        user_stats={"caption": "hi", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="flop",
    )
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "hook_analysis" in out


def test_select_sections_emits_script_structure_for_video_with_scenes() -> None:
    """A real video with a scene timeline but no script_structure *signal*
    (e.g. a 15s mukbang) still emits the structure section."""
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "scenes": [
                {"start": 0.0, "end": 5.0, "subject": "face"},
                {"start": 5.0, "end": 15.0, "subject": "food"},
            ],
        },
        user_stats={"caption": "mukbang", "views": 1_000_000, "video_id": "1"},
        reference_videos=[],
        channel_context=None,
        performance_tier="hit",
        content_format="mukbang",
    )
    manifest = build_signal_manifest(ctx)
    assert not manifest.get("script_structure"), "fixture should have no script signal"
    out = select_sections_to_emit(manifest, ctx)
    assert "script_structure" in out


def test_select_sections_skips_script_structure_for_carousel() -> None:
    """Carousels use slides, not a video timeline — no forced structure block."""
    ctx = build_diagnosis_ctx(
        user_analysis={
            "promotion_type": "organic",
            "slides": [{"index": 0}, {"index": 1}],
        },
        user_stats={"caption": "carousel", "views": 1000, "video_id": "2"},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        content_format="carousel",
    )
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "script_structure" not in out


def test_v6_section_body_and_narrative() -> None:
    diag = {
        "headline_vi": "Hook yếu so với mẫu.",
        "sections": [
            {
                "section_id": "diagnosis",
                "title": "Vấn đề chính",
                "text": "Đoạn một giải thích.\n\nĐoạn hai chi tiết.",
            }
        ],
    }
    body, nv = _v6_section_body_and_narrative(diag)
    assert "###" in body
    assert nv["_schema_version"] == "v6"
    assert nv["van_de_chinh"]
    assert nv["loi_chinh_narrative"][0]["error_id"] == "v6_summary"


def test_diagnosis_v6_word_budget_exceeded_on_long_section() -> None:
    diag = {
        "sections": [
            {"section_id": "diagnosis", "text": "word " * 100},
        ],
    }
    assert diagnosis_v6_word_budget_exceeded(diag) is True


def test_diagnosis_v6_script_structure_allows_120_word_prose() -> None:
    diag = {
        "sections": [
            {"section_id": "script_structure", "text": "word " * 120},
        ],
    }
    assert diagnosis_v6_word_budget_exceeded(diag) is False

    diag_long = {
        "sections": [
            {"section_id": "script_structure", "text": "word " * 130},
        ],
    }
    assert diagnosis_v6_word_budget_exceeded(diag_long) is True


def test_diagnosis_v6_hook_analysis_allows_100_word_prose() -> None:
    diag = {
        "sections": [
            {"section_id": "hook_analysis", "text": "word " * 100},
        ],
    }
    assert diagnosis_v6_word_budget_exceeded(diag) is False

    diag_long = {
        "sections": [
            {"section_id": "hook_analysis", "text": "word " * 112},
        ],
    }
    assert diagnosis_v6_word_budget_exceeded(diag_long) is True


def test_diagnosis_v6_word_budget_ok_when_brief() -> None:
    diag = {
        "sections": [
            {
                "section_id": "diagnosis",
                "text": "**Verdict.** " + "ngắn " * 8,
                "findings": [
                    {
                        "title_vi": "Hook yếu",
                        "body_vi": "1 câu.",
                        "fix_vi": "Đổi hook.",
                    }
                ],
            },
        ],
    }
    assert diagnosis_v6_word_budget_exceeded(diag) is False


def test_score_diagnosis_output_v6_ok() -> None:
    diag = {
        "headline_vi": "X",
        "sections": [
            {"section_id": "diagnosis", "text": "**Verdict.** " + "ngắn " * 8},
        ],
        "evidence_anchors": [
            {
                "signal_id": "a",
                "section_id": "diagnosis",
                "type": "user_analysis_field",
                "quote": "q",
            }
        ],
    }
    scored = score_diagnosis_output_v6(diag, section_ids_expected=["diagnosis"])
    assert scored["valid"] is True
    assert scored["section_discipline"] == 1.0


def test_validate_diagnosis_vi_citations_strips_unallowed_aweme() -> None:
    from getviews_pipeline.gemini import _validate_diagnosis_vi_citations

    bad = "9999999999999999999"
    diag: dict = {
        "headline_vi": "x",
        "sections": [
            {
                "section_id": "niche_pattern",
                "embedded_tiles": [{"aweme_id": bad}],
            }
        ],
        "evidence_anchors": [
            {"type": "aweme_id", "quote": bad, "location": bad},
            {"type": "user_analysis_field", "quote": "retention_ok", "location": None},
        ],
    }
    good = "1111111111111111111"
    _validate_diagnosis_vi_citations(diag, {good})
    assert diag["evidence_anchors"][0]["quote"] is None
    assert diag["evidence_anchors"][0]["location"] is None
    assert diag["evidence_anchors"][1]["quote"] == "retention_ok"
    assert diag["sections"][0]["embedded_tiles"][0]["aweme_id"] is None


def test_validate_diagnosis_vi_citations_keeps_allowed_pool() -> None:
    from getviews_pipeline.gemini import _validate_diagnosis_vi_citations

    aid = "1111111111111111111"
    diag: dict = {
        "headline_vi": "x",
        "sections": [{"embedded_tiles": [{"aweme_id": aid}]}],
        "evidence_anchors": [{"type": "aweme_id", "quote": aid, "location": aid}],
    }
    _validate_diagnosis_vi_citations(diag, {aid})
    assert diag["evidence_anchors"][0]["quote"] == aid
    assert diag["evidence_anchors"][0]["location"] == aid
    assert diag["sections"][0]["embedded_tiles"][0]["aweme_id"] == aid


def test_validate_narrative_citations_invokes_diagnosis_vi_guard() -> None:
    from getviews_pipeline.gemini import _validate_narrative_citations

    bad = "9999999999999999999"
    nv: dict = {
        "diagnosis_vi": {
            "headline_vi": "h",
            "sections": [],
            "evidence_anchors": [{"type": "aweme_id", "quote": bad, "location": None}],
        },
        "loi_chinh_narrative": [],
    }
    _validate_narrative_citations(nv, None, set())
    assert nv["diagnosis_vi"]["evidence_anchors"][0]["quote"] is None


def test_clamp_finding_evidence_refs_clamps_to_duration() -> None:
    diag: dict = {
        "sections": [
            {
                "findings": [
                    {"title_vi": "ok", "evidence_ref": {"start_sec": -1, "end_sec": 99, "label_vi": "x"}},
                ]
            }
        ]
    }
    _clamp_finding_evidence_refs(diag, 28.0)
    ref = diag["sections"][0]["findings"][0]["evidence_ref"]
    assert ref == {"start_sec": 0.0, "end_sec": 28.0, "label_vi": "x"}


def test_clamp_finding_evidence_refs_drops_unordered_and_garbage() -> None:
    diag: dict = {
        "sections": [
            {
                "findings": [
                    {"title_vi": "a", "evidence_ref": {"start_sec": 5, "end_sec": 3}},
                    {"title_vi": "b", "evidence_ref": "nope"},
                    {"title_vi": "c", "evidence_ref": {"start_sec": "NaN", "end_sec": None}},
                ]
            }
        ]
    }
    _clamp_finding_evidence_refs(diag, 28.0)
    fs = diag["sections"][0]["findings"]
    # Unordered end<=start drops end_sec, keeps start.
    assert fs[0]["evidence_ref"] == {"start_sec": 5.0}
    # Non-dict ref → None.
    assert fs[1]["evidence_ref"] is None
    # Both unusable → None.
    assert fs[2]["evidence_ref"] is None


def test_clamp_finding_evidence_refs_without_duration_keeps_valid_range() -> None:
    diag: dict = {
        "sections": [
            {"findings": [{"title_vi": "a", "evidence_ref": {"start_sec": 2, "end_sec": 6}}]}
        ]
    }
    _clamp_finding_evidence_refs(diag, None)
    assert diag["sections"][0]["findings"][0]["evidence_ref"] == {
        "start_sec": 2.0,
        "end_sec": 6.0,
    }
