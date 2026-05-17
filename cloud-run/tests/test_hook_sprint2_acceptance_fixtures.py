"""Sprint 2 §3 plan acceptance — six labeled analysis fixtures (offline, no TikTok fetch).

Each fixture represents post-extraction ``user_analysis.hook_analysis`` as Gemini would
emit (new hook types + supporting fields). Validates Pydantic + signal routing +
optional section-pool inclusion. Real network TikTok end-to-end remains optional;
this closes the QA gap for schema and deterministic signal behaviour.
"""

from __future__ import annotations

from getviews_pipeline.diagnose_sections import select_sections_to_emit
from getviews_pipeline.models import HookAnalysis
from getviews_pipeline.output_redesign import HOOK_TYPE_VI
from getviews_pipeline.signals.hook import extract_hook_signals
from getviews_pipeline.signals.registry import build_diagnosis_ctx, build_signal_manifest


def _niche_meta_excluding(hook_type: str, n: int = 100) -> dict:
    """Corpus hook_distribution top-3 that deliberately excludes ``hook_type``."""
    return {
        "sample_size": n,
        "hook_distribution": {
            "how_to": 40,
            "curiosity_gap": 35,
            "bold_claim": 25,
        },
    }


def _ctx(hook_analysis: dict, *, niche_meta: dict | None = None) -> dict:
    ua = {"promotion_type": "organic", "hook_analysis": hook_analysis}
    return build_diagnosis_ctx(
        user_analysis=ua,
        user_stats={"caption": "", "views": 1},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        niche_meta=niche_meta,
    )


def test_fixture_vach_tran_validates_and_triggers_hook_niche_mismatch() -> None:
    ha = {
        "first_frame_type": "face_with_text",
        "hook_phrase": "Sự thật brand X cố tình giấu",
        "hook_type": "vach_tran",
        "hook_notes": "",
        "hook_timeline": [],
        "hook_layering": "dual",
    }
    HookAnalysis.model_validate(ha)
    assert HOOK_TYPE_VI.get("vach_tran")
    ctx = _ctx(ha, niche_meta=_niche_meta_excluding("vach_tran"))
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_type_niche_mismatch" in ids


def test_fixture_gia_soc_compliance_price_manipulation() -> None:
    ha = {
        "first_frame_type": "product",
        "hook_phrase": "Chỉ 59k — giá gốc gạch 590k",
        "hook_type": "gia_soc",
        "hook_notes": "",
        "hook_timeline": [],
        "price_anchor_manipulation_suspected": True,
    }
    HookAnalysis.model_validate(ha)
    assert HOOK_TYPE_VI.get("gia_soc")
    ctx = _ctx(ha)
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_gia_soc_price_anchor_risk" in ids
    sig = next(s for s in extract_hook_signals(ctx) if s.id == "hook_gia_soc_price_anchor_risk")
    assert sig.section_id == "compliance"


def test_fixture_dialect_identity_without_markers() -> None:
    ha = {
        "first_frame_type": "face",
        "hook_phrase": "Người miền Nam hay làm thế này…",
        "hook_type": "dialect_identity",
        "hook_notes": "",
        "hook_timeline": [],
        "dialect_detected": "none",
    }
    HookAnalysis.model_validate(ha)
    assert HOOK_TYPE_VI.get("dialect_identity")
    ctx = _ctx(ha)
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_dialect_hook_without_markers" in ids


def test_fixture_fomo_urgency_niche_mismatch() -> None:
    ha = {
        "first_frame_type": "face_with_text",
        "hook_phrase": "Trend này sắp hết — làm ngay trong 24h",
        "hook_type": "fomo_urgency",
        "hook_notes": "",
        "hook_timeline": [],
        "hook_layering": "triple",
    }
    HookAnalysis.model_validate(ha)
    assert HOOK_TYPE_VI.get("fomo_urgency")
    ctx = _ctx(ha, niche_meta=_niche_meta_excluding("fomo_urgency"))
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_type_niche_mismatch" in ids


def test_fixture_tips_value_niche_mismatch() -> None:
    ha = {
        "first_frame_type": "face",
        "hook_phrase": "3 mẹo giúp da bớt dầu trong 1 tuần",
        "hook_type": "tips_value",
        "hook_notes": "",
        "hook_timeline": [],
    }
    HookAnalysis.model_validate(ha)
    assert HOOK_TYPE_VI.get("tips_value")
    ctx = _ctx(ha, niche_meta=_niche_meta_excluding("tips_value"))
    ids = [s.id for s in extract_hook_signals(ctx)]
    assert "hook_type_niche_mismatch" in ids


def test_fixture_mixed_gia_soc_layering_emits_hook_and_compliance_signals() -> None:
    """Giá sốc + neo nghi vấn + hook đơn lớp — compliance + hook_analysis paths."""
    ha = {
        "first_frame_type": "product",
        "hook_phrase": "Sale 39k, gạch 399k, ship free",
        "hook_type": "gia_soc",
        "hook_notes": "",
        "hook_timeline": [],
        "hook_layering": "single",
        "price_anchor_manipulation_suspected": True,
    }
    HookAnalysis.model_validate(ha)
    ctx = _ctx(ha)
    sigs = extract_hook_signals(ctx)
    ids = [s.id for s in sigs]
    assert "hook_gia_soc_price_anchor_risk" in ids
    assert "hook_layering_single" in ids
    manifest = build_signal_manifest(ctx)
    out = select_sections_to_emit(manifest, ctx)
    assert "hook_analysis" in out


def test_fixture_new_hook_types_have_vi_labels_in_synthesis_map() -> None:
    for slug in ("vach_tran", "gia_soc", "dialect_identity", "fomo_urgency", "tips_value"):
        label = HOOK_TYPE_VI.get(slug)
        assert label and isinstance(label, str) and len(label.strip()) > 0
