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
