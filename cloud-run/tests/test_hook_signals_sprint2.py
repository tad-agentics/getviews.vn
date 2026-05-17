"""Sprint 2 — Vietnam hook taxonomy signals + corpus hook normalization."""

from __future__ import annotations

from getviews_pipeline.corpus_ingest import _normalize_hook_type
from getviews_pipeline.models import HookAnalysis, VideoAnalysis
from getviews_pipeline.signals.hook import extract_hook_signals


def _minimal_ua_hook(**ha_overrides: object) -> dict:
    ha = {
        "first_frame_type": "face",
        "hook_phrase": "test",
        "hook_type": "question",
        "hook_notes": "",
        "hook_timeline": [],
    }
    ha.update(ha_overrides)
    return {"user_analysis": {"hook_analysis": ha}}


def test_normalize_hook_type_canonical_and_alias() -> None:
    assert _normalize_hook_type("gia_soc") == "gia_soc"
    assert _normalize_hook_type("price_shock") == "gia_soc"
    assert _normalize_hook_type("bold_claim") == "bold_claim"
    assert _normalize_hook_type("not_a_real_hook") == "other"


def test_hook_analysis_unknown_hook_layering_becomes_none() -> None:
    ha = HookAnalysis.model_validate(
        {
            "first_frame_type": "face",
            "hook_phrase": "x",
            "hook_type": "how_to",
            "hook_notes": "",
            "hook_timeline": [],
            "hook_layering": "double",
        }
    )
    assert ha.hook_layering is None


def test_extract_gia_soc_compliance_signal() -> None:
    ctx = _minimal_ua_hook(
        hook_type="gia_soc",
        price_anchor_manipulation_suspected=True,
    )
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_gia_soc_price_anchor_risk" in ids
    assert any(s.section_id == "compliance" for s in extract_hook_signals(ctx))


def test_extract_price_shock_alias_compliance_signal() -> None:
    ctx = _minimal_ua_hook(
        hook_type="price_shock",
        price_anchor_manipulation_suspected=True,
    )
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_gia_soc_price_anchor_risk" in ids


def test_extract_hook_layering_single() -> None:
    ctx = _minimal_ua_hook(hook_layering="single")
    sigs = extract_hook_signals(ctx)
    ids = [s.id for s in sigs]
    assert "hook_layering_single" in ids
    layering = [s for s in sigs if s.id == "hook_layering_single"]
    assert layering and layering[0].section_id == "hook_analysis"


def test_extract_hook_body_contract_violated() -> None:
    ctx = _minimal_ua_hook(hook_body_contract=False)
    sigs = extract_hook_signals(ctx)
    ids = [s.id for s in sigs]
    assert "hook_body_contract_violated" in ids
    row = [s for s in sigs if s.id == "hook_body_contract_violated"][0]
    assert row.section_id == "hook_analysis"


def test_extract_dialect_identity_without_markers() -> None:
    ctx = _minimal_ua_hook(hook_type="dialect_identity", dialect_detected="none")
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_dialect_hook_without_markers" in ids


def test_video_analysis_accepts_sprint2_hook_fields() -> None:
    d = {
        "hook_analysis": {
            "first_frame_type": "face",
            "hook_phrase": "x",
            "hook_type": "vach_tran",
            "hook_notes": "",
            "hook_timeline": [],
            "hook_layering": "dual",
            "hook_body_contract": True,
            "dialect_detected": "southern",
            "price_anchor_manipulation_suspected": False,
        },
        "has_human_speaking_to_camera": True,
        "has_expressed_opinion_or_question": False,
        "text_overlays": [],
        "scenes": [{"type": "face_to_camera", "start": 0.0, "end": 5.0}],
        "transitions_per_second": 0.2,
        "energy_level": "medium",
        "key_timestamps": [],
        "audio_transcript": "a",
        "tone": "conversational",
        "topics": [],
        "key_messages": [],
        "cta": None,
        "content_direction": {"what_works": "x", "suggested_angles": []},
        "target_audience": "",
        "pain_points": [],
        "promotion_type": "organic",
        "style_tags": [],
    }
    m = VideoAnalysis.model_validate(d)
    assert m.hook_analysis.hook_type == "vach_tran"
    assert m.hook_analysis.hook_layering == "dual"
