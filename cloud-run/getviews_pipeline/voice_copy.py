"""Post-process Gemini narrative strings — replace stats jargon with creator Vietnamese."""

from __future__ import annotations

import re
from typing import Any

_CHANNEL_MEDIAN = "mức view thường trên kênh"
_NICHE_MEDIAN = "mức view thường trong ngách"
_GENERIC_MEDIAN = "mức view thường"

_P90_RE = re.compile(r"\bp90\b", re.IGNORECASE)
_P75_RE = re.compile(r"\bp75\b", re.IGNORECASE)
_P50_RE = re.compile(r"\bp50\b", re.IGNORECASE)
_P25_RE = re.compile(r"\bp25\b", re.IGNORECASE)
_MEDIAN_VIEWS_CHANNEL_RE = re.compile(
    r"(?:median|trung vị)\s+([\d.,]+)\s*view\s+của kênh",
    re.IGNORECASE,
)
_MEDIAN_CHANNEL_RE = re.compile(r"(?:median|trung vị)\s+kênh", re.IGNORECASE)
_MEDIAN_NICHE_RE = re.compile(r"(?:median|trung vị)\s+ngách", re.IGNORECASE)
_TIMES_MEDIAN_NICHE_RE = re.compile(r"×\s*(?:median|trung vị)\s+ngách", re.IGNORECASE)
_TIMES_MEDIAN_RE = re.compile(r"×\s*(?:median|trung vị)", re.IGNORECASE)
_VS_MEDIAN_RE = re.compile(r"so với\s+(?:median|trung vị)", re.IGNORECASE)
_BELOW_MEDIAN_RE = re.compile(r"dưới\s+(?:median|trung vị)", re.IGNORECASE)
_ABOVE_MEDIAN_RE = re.compile(r"trên\s+(?:median|trung vị)", re.IGNORECASE)
_MEDIAN_RE = re.compile(r"\bmedian\b", re.IGNORECASE)
_TRUNG_VI_RE = re.compile(r"trung vị", re.IGNORECASE)

# English jargon + raw enum codes that the synthesis still echoes despite the
# voice_guide steering block. Mirrors getviews_pipeline/voice_guide.py — keep
# in sync. Whole-word, case-insensitive; multi-word phrases listed before the
# single words they contain so the longer match wins.
_JARGON_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpattern[\s_-]?interrupt\b", re.IGNORECASE), "ngắt nhịp"),
    (re.compile(r"\boverlay checklist\b", re.IGNORECASE), "danh sách bước trên màn hình"),
    (re.compile(r"\btext[\s_-]?overlay\b", re.IGNORECASE), "chữ trên màn hình"),
    (re.compile(r"\bface[\s_-]?enter\b", re.IGNORECASE), "khuôn mặt xuất hiện"),
    (re.compile(r"\bentertainment[\s_-]?first\b", re.IGNORECASE), "giải trí là chính"),
    (re.compile(r"\bdead[\s_-]?air\b", re.IGNORECASE), "khoảng lặng"),
    (re.compile(r"\bjump[\s_-]?cut\b", re.IGNORECASE), "cắt giật"),
    (re.compile(r"\barchetypes?\b", re.IGNORECASE), "hình mẫu"),
    (re.compile(r"\bbookmarks?\b", re.IGNORECASE), "lưu"),
    (re.compile(r"\bexperts?\b", re.IGNORECASE), "chuyên gia"),
    (re.compile(r"\btutorials?\b", re.IGNORECASE), "hướng dẫn"),
    (re.compile(r"\bheatmaps?\b", re.IGNORECASE), "bản đồ nhiệt"),
    (re.compile(r"\bcorpus\b", re.IGNORECASE), "kho video"),
)


def humanize_stats_prose(text: str) -> str:
    """Replace percentile / median jargon in user-facing diagnosis prose."""
    if not text or not text.strip():
        return text
    out = text
    out = _P90_RE.sub("mức rất cao trong ngách (top 10%)", out)
    out = _P75_RE.sub("mức cao trong ngách (top 25%)", out)
    out = _P25_RE.sub("mức thấp trong ngách (bottom 25%)", out)
    out = _P50_RE.sub("mức giữa ngách", out)
    out = _MEDIAN_VIEWS_CHANNEL_RE.sub(
        rf"{_CHANNEL_MEDIAN} (khoảng \1 lượt xem)",
        out,
    )
    out = _MEDIAN_CHANNEL_RE.sub(_CHANNEL_MEDIAN, out)
    out = _MEDIAN_NICHE_RE.sub(_NICHE_MEDIAN, out)
    out = _TIMES_MEDIAN_NICHE_RE.sub(f"× {_NICHE_MEDIAN}", out)
    out = _TIMES_MEDIAN_RE.sub(f"× {_GENERIC_MEDIAN}", out)
    out = _VS_MEDIAN_RE.sub(f"so với {_GENERIC_MEDIAN}", out)
    out = _BELOW_MEDIAN_RE.sub(f"dưới {_GENERIC_MEDIAN}", out)
    out = _ABOVE_MEDIAN_RE.sub(f"trên {_GENERIC_MEDIAN}", out)
    out = _MEDIAN_RE.sub(_GENERIC_MEDIAN, out)
    out = _TRUNG_VI_RE.sub(_GENERIC_MEDIAN, out)
    for pattern, replacement in _JARGON_SUBS:
        out = pattern.sub(replacement, out)
    return out


def humanize_narrative_vi_dict(narrative_vi: dict[str, Any] | None) -> dict[str, Any] | None:
    """Walk narrative_vi (incl. nested diagnosis_vi sections) and humanize all strings."""

    def _walk(obj: Any) -> Any:
        if isinstance(obj, str):
            return humanize_stats_prose(obj)
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        return obj

    if not narrative_vi:
        return narrative_vi
    result = _walk(narrative_vi)
    return result if isinstance(result, dict) else narrative_vi
