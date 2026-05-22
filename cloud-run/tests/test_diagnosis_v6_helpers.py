"""Unit tests for diagnosis section pool + v6 narrative envelope helpers."""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.diagnosis_quality import score_diagnosis_output_v6
from getviews_pipeline.gemini import _v6_section_body_and_narrative
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
    assert "next_video" in out
    assert out.index("diagnosis") < out.index("next_video")


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
    out = select_sections_to_emit(manifest, ctx, depth="deep")
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
    out = select_sections_to_emit(manifest, ctx, depth="deep")
    assert "hook_analysis" in out
    assert out.index("diagnosis") < out.index("hook_analysis")
    assert "commerce" in out
    assert out.index("hook_analysis") < out.index("commerce")


def test_select_sections_omits_hook_analysis_when_only_low_salience_hook_signal() -> None:
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
    assert "hook_analysis" not in out


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


def test_score_diagnosis_output_v6_ok() -> None:
    diag = {
        "headline_vi": "X",
        "sections": [
            {"section_id": "diagnosis", "text": "word " * 80},
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
