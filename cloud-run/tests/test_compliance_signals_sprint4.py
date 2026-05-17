"""Sprint 4 §10 — compliance scan + compliance-section signals."""

from __future__ import annotations

from getviews_pipeline.compliance import (
    _k_values_vnd,
    _normalize_text,
    collect_compliance_flags,
)
from getviews_pipeline.signals.compliance import extract_compliance_signals
from getviews_pipeline.signals.registry import build_diagnosis_ctx


def _ctx(
    *,
    ua: dict,
    st: dict | None = None,
    ch: dict | None = None,
    flags: list[dict] | None = None,
) -> dict:
    st = st or {"caption": "", "views": 1000}
    fl = flags if flags is not None else collect_compliance_flags(ua, st)
    return build_diagnosis_ctx(
        user_analysis=ua,
        user_stats=st,
        reference_videos=[],
        channel_context=ch,
        performance_tier="average",
        compliance_flags=fl,
    )


def test_restricted_health_claim_salience_high() -> None:
    ua = {
        "promotion_type": "organic",
        "audio_transcript": "Sản phẩm này cam kết khỏi hẳn sau 7 ngày",
        "text_overlays": [],
    }
    ctx = _ctx(ua=ua)
    sigs = extract_compliance_signals(ctx)
    ids = {s.id for s in sigs}
    assert "compliance_restricted_phrase" in ids
    sig = next(s for s in sigs if s.id == "compliance_restricted_phrase")
    assert sig.salience == 1.0


def test_restricted_price_guarantee() -> None:
    ua = {
        "promotion_type": "organic",
        "audio_transcript": "Shop em giá rẻ nhất thị trường luôn nha",
        "text_overlays": [],
    }
    ctx = _ctx(ua=ua)
    assert any(s.id == "compliance_restricted_phrase" for s in extract_compliance_signals(ctx))


def test_restricted_off_platform_in_overlay() -> None:
    ua = {
        "promotion_type": "organic",
        "audio_transcript": "",
        "text_overlays": [{"text": "Đặt hàng add zalo 0909", "appears_at": 0.0}],
    }
    ctx = _ctx(ua=ua)
    assert any(s.id == "compliance_restricted_phrase" for s in extract_compliance_signals(ctx))


def test_disclosure_compliance_section() -> None:
    ua = {
        "promotion_type": "organic",
        "commerce_intent": {
            "conversion_objective": "affiliate_shopee",
            "product_price_tier": "under_150k",
            "creator_type": "koc",
            "verbal_cta_present": True,
            "disclosure_present": False,
            "disclosure_form": "none",
        },
        "text_overlays": [],
    }
    ctx = _ctx(ua=ua, flags=[])
    sigs = extract_compliance_signals(ctx)
    ids = [s.id for s in sigs]
    assert "compliance_ad_law_disclosure_missing" in ids
    disc = next(s for s in sigs if s.id == "compliance_ad_law_disclosure_missing")
    assert disc.salience == 0.9


def test_inflated_price_anchor_numeric() -> None:
    ua = {
        "promotion_type": "organic",
        "audio_transcript": "Giá gốc 500k hôm nay chỉ 99k thôi",
        "text_overlays": [],
    }
    ctx = _ctx(ua=ua)
    assert any(s.id == "compliance_price_anchor_inflated" for s in extract_compliance_signals(ctx))


def test_k_values_vnd_plain_1000k_not_trailing_zeros() -> None:
    """Regression: old regex matched '000k' inside '1000k' and dropped the amount."""
    n = _normalize_text("Giá gốc 1000k hôm nay chỉ 100k")
    assert sorted(_k_values_vnd(n)) == [100_000, 1_000_000]


def test_k_values_vnd_dot_thousands() -> None:
    n = _normalize_text("Neo 1.000k sale 100k")
    assert sorted(_k_values_vnd(n)) == [100_000, 1_000_000]


def test_inflated_price_anchor_unformatted_1000k_vs_100k() -> None:
    ua = {
        "promotion_type": "organic",
        "audio_transcript": "Giá gốc 1000k hôm nay chỉ 100k",
        "text_overlays": [],
    }
    ctx = _ctx(ua=ua)
    assert any(s.id == "compliance_price_anchor_inflated" for s in extract_compliance_signals(ctx))


def test_shadowban_cheo_heuristic() -> None:
    ua = {"promotion_type": "organic", "audio_transcript": "", "text_overlays": []}
    st = {"caption": "", "views": 30_000, "engagement_rate": 0.09, "retention_end_pct": 40.0}
    ch = {"available": True, "median_views": 100_000.0, "sample_size": 5}
    ctx = _ctx(ua=ua, st=st, ch=ch, flags=[])
    ids = [s.id for s in extract_compliance_signals(ctx)]
    assert "compliance_shadowban_cheo_signature" in ids
