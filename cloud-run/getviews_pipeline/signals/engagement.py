"""§9 Engagement architecture signals (metadata / diagnosis sections)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_HIT_TIER = "hit"
_COMMENT_HOOK_RE = re.compile(
    r"\?|bình\s*luận|comment|cho\s+mình\s+biết|các\s+bạn\s+nghĩ|"
    r"bạn\s+nào|ai\s+biết|trả\s+lời",
    re.IGNORECASE,
)
_SAVEABLE_FORMATS = frozenset(
    {"how_to", "tutorial", "listicle", "checklist", "recipe", "tips", "education"}
)


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


def _as_commerce_dict(ua: dict) -> dict[str, Any]:
    raw = ua.get("commerce_intent")
    return raw if isinstance(raw, dict) else {}


def _is_commercial(ua: dict, ci: dict[str, Any]) -> bool:
    promo = str(ua.get("promotion_type") or "organic").lower()
    if promo not in ("organic", ""):
        return True
    obj = str(ci.get("conversion_objective") or "entertainment_first").lower()
    return obj != "entertainment_first"


def extract_pinned_comment_signal(ctx: dict) -> list[Signal]:
    """Slide-in when stats carry a pinned comment line but VO does not reference it."""
    ua = ctx.get("user_analysis") if isinstance(ctx.get("user_analysis"), dict) else {}
    st = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    ci = _as_commerce_dict(ua)
    if not _is_commercial(ua, ci):
        return []
    pin = str(st.get("pinned_comment_text") or "").strip()
    if len(pin) < 8:
        return []
    tr = _norm(str(ua.get("audio_transcript") or ""))
    excerpt = _norm(pin[:120])
    if excerpt and excerpt in tr:
        return []
    return [
        Signal(
            id="engagement_pinned_comment_not_in_vo",
            section_id="metadata",
            taxonomy_ref="§9",
            salience=0.55,
            claim="Có bình luận ghim nhưng giọng nói không nhắc — bỏ lỡ luồng CTA/ưu đãi thường thấy trên TikTok Shop.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=pin[:200],
                    location="user_stats.pinned_comment_text",
                )
            ],
            suggested_fix="Lồng 1 câu trong VO trỏ rõ comment ghim (mã, link, Q&A).",
        )
    ]


def extract_loop_architecture_signal(ctx: dict) -> list[Signal]:
    """Positive: open/close frame similarity (Gemini 0–1) suggests loop-friendly edit."""
    ua = ctx.get("user_analysis") if isinstance(ctx.get("user_analysis"), dict) else {}
    raw = ua.get("loop_architecture_score")
    if raw is None or raw == "":
        return []
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return []
    if v < 0.72:
        return []
    return [
        Signal(
            id="engagement_loop_architecture_positive",
            section_id="metadata",
            taxonomy_ref="§9",
            salience=0.4,
            claim=(
                f"Khung mở–đóng khá khớp (điểm {v:.2f}) — tiềm năng loop/rewatch tốt."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"loop_architecture_score={v}",
                    location="user_analysis.loop_architecture_score",
                )
            ],
            suggested_fix="Giữ beat cuối khớp hook để lặp mượt; tránh chèn watermark che điểm nối.",
        )
    ]


def extract_comment_hook_missing_signal(ctx: dict) -> list[Signal]:
    """P1 — transcript thiếu CTA hỏi / kích comment."""
    ua = ctx.get("user_analysis") if isinstance(ctx.get("user_analysis"), dict) else {}
    tr = str(ua.get("audio_transcript") or "").strip()
    if len(tr) < 20:
        return []
    if _COMMENT_HOOK_RE.search(tr):
        return []
    return [
        Signal(
            id="engagement_comment_hook_missing",
            section_id="metadata",
            taxonomy_ref="§9",
            salience=0.56,
            claim="Thoại không có câu hỏi/CTA kích comment — bỏ lỡ tín hiệu tương tác sớm.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"transcript_len={len(tr)} comment_hook=false",
                    location="user_analysis.audio_transcript",
                )
            ],
            suggested_fix='Thêm 1 câu hỏi mở cuối hook (VD: "Bạn nào từng gặp?" / "Comment số 1 nếu…").',
        )
    ]


def extract_save_trigger_weak_signal(ctx: dict) -> list[Signal]:
    """P1 — hit tier nhưng thiếu kiến trúc save (save_trigger_type)."""
    if str(ctx.get("performance_tier") or "").lower() != _HIT_TIER:
        return []
    ua = ctx.get("user_analysis") if isinstance(ctx.get("user_analysis"), dict) else {}
    raw = ua.get("save_trigger_type")
    sv = str(raw or "").strip().lower()
    if sv and sv not in ("none", "null", "other"):
        return []

    fmt = str(ctx.get("content_format") or ua.get("content_format") or "").lower()
    style_tags = {str(t).lower() for t in (ua.get("style_tags") or [])}
    saveable = fmt in _SAVEABLE_FORMATS or bool(style_tags & {"how_to", "tutorial_bookmark", "educational_slides"})
    if not saveable:
        return []

    return [
        Signal(
            id="engagement_save_trigger_weak",
            section_id="diagnosis",
            taxonomy_ref="§9",
            salience=0.61,
            claim=(
                f"Video hit tier `{fmt or 'saveable'}` nhưng thiếu trigger lưu rõ "
                "(checklist/deal/recipe) — bỏ lỡ bookmark intent."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"save_trigger_type={sv or 'none'} content_format={fmt}",
                    location="user_analysis.save_trigger_type+content_format",
                )
            ],
            suggested_fix="Thêm overlay checklist hoặc CTA “lưu lại công thức” trước beat cuối.",
        )
    ]


def extract_engagement_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_pinned_comment_signal(ctx))
    out.extend(extract_loop_architecture_signal(ctx))
    out.extend(extract_comment_hook_missing_signal(ctx))
    out.extend(extract_save_trigger_weak_signal(ctx))
    return out
