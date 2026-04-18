"""Unit tests for thumbnail_analysis pure helpers.

The Gemini call itself is integration-side (requires an API key + a frame
URL); these tests cover the text-clipping + cache-freshness helpers that
ship without network dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from getviews_pipeline.thumbnail_analysis import _truncate_text
from getviews_pipeline.thumbnail_analysis_cache import CACHE_TTL_DAYS, _is_fresh


# ── _truncate_text ─────────────────────────────────────────────────────────


def test_truncate_none_returns_none() -> None:
    assert _truncate_text(None, 40) is None


def test_truncate_empty_or_whitespace_becomes_none() -> None:
    assert _truncate_text("", 40) is None
    assert _truncate_text("    ", 40) is None


def test_truncate_under_limit_unchanged() -> None:
    assert _truncate_text("Hay quá", 40) == "Hay quá"


def test_truncate_exact_limit_unchanged() -> None:
    s = "a" * 40
    assert _truncate_text(s, 40) == s


def test_truncate_over_limit_ellipsized() -> None:
    s = "Chạy vì hook mở đầu cận mặt biểu cảm ngạc nhiên đậm"
    out = _truncate_text(s, 40)
    assert out is not None
    assert len(out) <= 40
    assert out.endswith("…")


def test_truncate_preserves_vietnamese_diacritics() -> None:
    s = "Mặt lớn + chữ vàng trên đen"
    assert _truncate_text(s, 40) == s


# ── _is_fresh ─────────────────────────────────────────────────────────────


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_is_fresh_recent_ok() -> None:
    recent = datetime.now(tz=timezone.utc) - timedelta(days=3)
    assert _is_fresh(_iso(recent)) is True


def test_is_fresh_exactly_at_ttl_still_ok() -> None:
    edge = datetime.now(tz=timezone.utc) - timedelta(days=CACHE_TTL_DAYS - 1)
    assert _is_fresh(_iso(edge)) is True


def test_is_fresh_past_ttl_rejected() -> None:
    stale = datetime.now(tz=timezone.utc) - timedelta(days=CACHE_TTL_DAYS + 5)
    assert _is_fresh(_iso(stale)) is False


def test_is_fresh_none_rejected() -> None:
    assert _is_fresh(None) is False


def test_is_fresh_empty_string_rejected() -> None:
    assert _is_fresh("") is False


def test_is_fresh_malformed_rejected() -> None:
    assert _is_fresh("not-a-timestamp") is False


def test_is_fresh_accepts_z_suffix() -> None:
    recent = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    s = recent.isoformat().replace("+00:00", "Z")
    assert _is_fresh(s) is True


def test_is_fresh_naive_timestamp_treated_as_utc() -> None:
    naive = (datetime.utcnow() - timedelta(days=1)).isoformat()
    assert _is_fresh(naive) is True


def test_is_fresh_custom_ttl() -> None:
    age = datetime.now(tz=timezone.utc) - timedelta(days=10)
    assert _is_fresh(_iso(age), ttl_days=7) is False
    assert _is_fresh(_iso(age), ttl_days=30) is True


# ── ThumbnailAnalysis pydantic model ───────────────────────────────────────


def test_model_validates_minimum_fields() -> None:
    from getviews_pipeline.models import ThumbnailAnalysis  # type: ignore

    m = ThumbnailAnalysis.model_validate(
        {
            "stop_power_score": 7.5,
            "dominant_element": "face",
            "text_on_thumbnail": "ĐỪNG MUA KEM",
            "facial_expression": "surprised",
            "colour_contrast": "high",
            "why_it_stops": "Mặt lớn + chữ vàng trên đen — dừng scroll.",
        }
    )
    assert m.stop_power_score == 7.5
    assert m.dominant_element == "face"


def test_model_rejects_out_of_range_score() -> None:
    from getviews_pipeline.models import ThumbnailAnalysis  # type: ignore
    from pydantic import ValidationError

    try:
        ThumbnailAnalysis.model_validate(
            {
                "stop_power_score": 15.0,
                "dominant_element": "text",
                "colour_contrast": "high",
                "why_it_stops": "Chữ lớn.",
            }
        )
        raised = False
    except ValidationError:
        raised = True
    assert raised


def test_model_allows_null_face_fields() -> None:
    from getviews_pipeline.models import ThumbnailAnalysis  # type: ignore

    m = ThumbnailAnalysis.model_validate(
        {
            "stop_power_score": 5.0,
            "dominant_element": "product",
            "text_on_thumbnail": None,
            "facial_expression": None,
            "colour_contrast": "medium",
            "why_it_stops": "Sản phẩm trung tính, không có chữ.",
        }
    )
    assert m.text_on_thumbnail is None
    assert m.facial_expression is None
