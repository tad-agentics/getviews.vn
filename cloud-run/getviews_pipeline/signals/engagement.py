"""§9 Engagement architecture signals (distribution section)."""

from __future__ import annotations

import unicodedata
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal


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
            section_id="distribution",
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
            section_id="distribution",
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


def extract_engagement_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_pinned_comment_signal(ctx))
    out.extend(extract_loop_architecture_signal(ctx))
    return out
