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
# Content-format slugs Gemini echoes in prose — mirrors
# src/lib/contentFormatLabels.ts + enum_labels_vi (never raw English labels).
_CONTENT_FORMAT_SLUG_VI: dict[str, str] = {
    "faceless": "không lộ mặt",
    "talking_head": "nói thẳng camera",
    "tutorial": "hướng dẫn",
    "review": "đánh giá",
    "haul": "mua sắm",
    "grwm": "chuẩn bị đi",
    "vlog": "vlog ngày",
    "before_after": "trước/sau",
    "pov": "góc nhìn POV",
    "storytime": "kể chuyện",
    "storytelling": "kể chuyện",
    "listicle": "danh sách",
    "mukbang": "mukbang",
    "recipe": "nấu ăn",
    "comparison": "so sánh",
    "comedy_skit": "tiểu phẩm",
    "outfit_transition": "phối đồ",
    "dance": "nhảy",
    "highlight": "tóm tắt clip",
    "gameplay": "chơi game",
    "lesson": "bài học",
}

_JARGON_SUBS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bpain[\s_-]?points?\b", re.IGNORECASE), "điểm nhạy"),
    (re.compile(r"\bpattern[\s_-]?interrupt\b", re.IGNORECASE), "ngắt nhịp"),
    (re.compile(r"\boverlay checklist\b", re.IGNORECASE), "danh sách bước trên màn hình"),
    (re.compile(r"\btext[\s_-]?overlay\b", re.IGNORECASE), "chữ trên màn hình"),
    (re.compile(r"\bface[\s_-]?enter\b", re.IGNORECASE), "khuôn mặt xuất hiện"),
    (re.compile(r"\bentertainment[\s_-]?first\b", re.IGNORECASE), "giải trí là chính"),
    (re.compile(r"\bdead[\s_-]?air\b", re.IGNORECASE), "khoảng lặng"),
    (re.compile(r"\bjump[\s_-]?cut\b", re.IGNORECASE), "cắt giật"),
    (re.compile(r"\bdiscoverability\b", re.IGNORECASE), "khả năng được tìm thấy"),
    (re.compile(r"\bformat\s+['\"]faceless['\"]", re.IGNORECASE), "định dạng không lộ mặt"),
    (re.compile(r"\bformat\s+faceless\b", re.IGNORECASE), "định dạng không lộ mặt"),
    (re.compile(r"\barchetypes?\b", re.IGNORECASE), "hình mẫu"),
    (re.compile(r"\bbookmarks?\b", re.IGNORECASE), "lưu"),
    (re.compile(r"\bexperts?\b", re.IGNORECASE), "chuyên gia"),
    (re.compile(r"\btutorials?\b", re.IGNORECASE), "hướng dẫn"),
    (re.compile(r"\btemplates?\b", re.IGNORECASE), "mẫu"),
    (re.compile(r"\bpromises?\b", re.IGNORECASE), "lời hứa"),
    (re.compile(r"\btips?\b", re.IGNORECASE), "mẹo"),
    (re.compile(r"\bheatmaps?\b", re.IGNORECASE), "bản đồ nhiệt"),
    (re.compile(r"\bcorpus\b", re.IGNORECASE), "kho video"),
    (re.compile(r"\bformats?\b", re.IGNORECASE), "định dạng"),
    (re.compile(r"\bprice[\s_-]?anchor\b", re.IGNORECASE), "neo giá"),
    (re.compile(r"\bnegative[\s_-]?markers?\b", re.IGNORECASE), "dấu hiệu tiêu cực"),
    (re.compile(r"\b(?:audio[\s_-]?)?transcript\b", re.IGNORECASE), "lời thoại"),
    (re.compile(r"\bcuriousity[\s_-]?gap\b", re.IGNORECASE), "Tạo khoảng trống tò mò"),
    (re.compile(r"\bcompletion[\s_-]?rates?\b", re.IGNORECASE), "tỷ lệ xem hết"),
)


def _collapse_jargon_duplicates(text: str) -> str:
    """Remove redundant parentheticals after jargon → Vietnamese substitution."""
    text = re.sub(r"ngắt nhịp\s*\(\s*ngắt nhịp\s*\)", "ngắt nhịp", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\(\s*ngắt nhịp\s*\)\s*\(\s*ngắt nhịp\s*\)",
        "(ngắt nhịp)",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _substitute_enum_codes_in_prose(text: str) -> str:
    """Replace raw snake_case enum codes still echoed in synthesis prose."""
    from getviews_pipeline.enum_labels_vi import (
        CONVERSION_OBJECTIVE_VI,
        FIRST_FRAME_VI,
        HOOK_TYPE_VI,
        HOOK_TIMELINE_EVENT_VI,
        STYLE_TAG_VI,
    )

    merged: dict[str, str] = {}
    for table in (
        HOOK_TYPE_VI,
        CONVERSION_OBJECTIVE_VI,
        STYLE_TAG_VI,
        FIRST_FRAME_VI,
        HOOK_TIMELINE_EVENT_VI,
    ):
        merged.update(table)
    skip = frozenset({"none", "other", ""})
    for key in sorted(merged.keys(), key=len, reverse=True):
        if key in skip:
            continue
        slug_pat = re.escape(key).replace("_", r"[\s_-]")
        text = re.sub(rf"\b{slug_pat}\b", merged[key], text, flags=re.IGNORECASE)
    return text


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
    for slug, label in _CONTENT_FORMAT_SLUG_VI.items():
        slug_pat = slug.replace("_", r"[\s_-]")
        out = re.sub(rf"\b{slug_pat}\b", label, out, flags=re.IGNORECASE)
    out = _substitute_enum_codes_in_prose(out)
    return _collapse_jargon_duplicates(out)


_PROSE_FIELD_KEYS = frozenset({
    "headline_vi",
    "ket_luan_nhanh",
    "van_de_chinh",
    "dinh_huong_chien_luoc",
    "title_vi",
    "body_vi",
    "fix_vi",
    "text",
    "text_vi",
    "narrative_vi",
    "narrative",
    "title",
    "detail",
    "fix",
    "reason_vi",
    "premise_vi",
    "hook_vi",
    "format_name_vi",
    "mechanism_vi",
    "example_hook_vi",
    "caption_snippet",
    "desc",
    "question",
    "label",
})


def _humanize_string_fields(obj: Any) -> Any:
    """Recursively humanize known prose keys in dict/list trees."""
    if isinstance(obj, str):
        return humanize_stats_prose(obj)
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(v, str) and k in _PROSE_FIELD_KEYS:
                out[k] = humanize_stats_prose(v)
            else:
                out[k] = _humanize_string_fields(v)
        return out
    if isinstance(obj, list):
        return [_humanize_string_fields(v) for v in obj]
    return obj


def humanize_video_report_out(out: dict[str, Any] | None) -> dict[str, Any] | None:
    """Final-pass Vietnamese cleanup on every user-visible prose field in a video report."""
    if not out:
        return out
    narrative = out.get("narrative_vi")
    if isinstance(narrative, dict):
        cleaned = humanize_narrative_vi_dict(narrative)
        if cleaned is not None:
            out["narrative_vi"] = cleaned
    cards = out.get("format_cards")
    if isinstance(cards, list):
        out["format_cards"] = _humanize_string_fields(cards)
    for err_key in ("errors", "structural_errors"):
        errs = out.get(err_key)
        if isinstance(errs, list):
            out[err_key] = _humanize_string_fields(errs)
    enrich = out.get("enrichment")
    if isinstance(enrich, dict):
        if isinstance(enrich.get("target_audience"), str):
            enrich["target_audience"] = humanize_stats_prose(enrich["target_audience"])
        pp = enrich.get("pain_points")
        if isinstance(pp, list):
            enrich["pain_points"] = [
                humanize_stats_prose(p) if isinstance(p, str) else p for p in pp
            ]
    rq = out.get("related_questions")
    if isinstance(rq, list):
        out["related_questions"] = [
            humanize_stats_prose(q) if isinstance(q, str) else _humanize_string_fields(q)
            for q in rq
        ]
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
