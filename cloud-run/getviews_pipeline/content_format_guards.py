"""Guards for ``classify_format`` — foreign reup detection + commerce FP suppression.

Foreign-reup rows (creator re-uploads overseas footage with Vietnamese subtitles)
often trip commerce regexes (``mua.*về``, ``review``, ``mở hộp`` in overlay text)
even when the video is curation/commentary, not a native haul.
"""

from __future__ import annotations

import re
from typing import Any

# Commerce-oriented formats that subtitle text on reup clips commonly false-trigger.
_REUP_COMMERCE_FORMATS = frozenset({"haul", "review", "comparison"})

# format_axis (HI-9) → legacy content_format slug for reup curation clips.
_FORMAT_AXIS_TO_CONTENT_FORMAT: dict[str, str] = {
    "react_commentary": "highlight",
    "montage_highlights": "highlight",
    "pov_storytelling": "storytelling",
    "observational_relatable": "comedy_skit",
    "skit_scripted": "comedy_skit",
    "vlog_daily": "vlog",
    "tutorial": "tutorial",
    "talking_head_advice": "talking_head",
    "music_performance": "highlight",
    "dance_choreography": "dance",
    "review_unboxing": "review",  # only when commerce_intent confirms commerce
    "live_commerce": "haul",
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_VN_OVERLAY_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]",
    re.IGNORECASE,
)
# Strict — subtitle/dub heuristics; omits bare «quốc tế» (native travel vlogs).
_FOREIGN_TOPIC_STRICT_RE = re.compile(
    r"china|chinese|trung quốc|trung quoc|douyin|抖音|korean|hàn quốc|han quoc|"
    r"japanese|nhật bản|nhat ban|reup|re-upload|\bdub\b|dịch|phụ đề|phu de|lồng tiếng",
    re.IGNORECASE,
)

_REUP_FORMAT_AXES = frozenset({
    "react_commentary",
    "montage_highlights",
    "observational_relatable",
    "pov_storytelling",
})


def _commerce_intent_is_commerce(analysis: dict[str, Any]) -> bool:
    ci = analysis.get("commerce_intent")
    if not isinstance(ci, dict):
        return False
    tier = str(ci.get("product_price_tier") or "not_commerce").strip().lower()
    return tier not in ("", "not_commerce", "none", "unknown")


def _overlay_text_blob(analysis: dict[str, Any]) -> str:
    parts: list[str] = []
    for ov in analysis.get("text_overlays") or []:
        if isinstance(ov, dict):
            parts.append(str(ov.get("text") or ""))
    return " ".join(parts).lower()


def coerce_analysis_dict(raw: Any) -> dict[str, Any]:
    """Normalise corpus ``analysis_json`` (dict or JSON string) to a dict."""
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def refresh_video_content_format(
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_id: int,
) -> str | None:
    """Re-classify from live extraction; mutates ``video`` content_format + content_class_id."""
    if not niche_id or not analysis:
        return str(video.get("content_format") or "").strip() or None
    from getviews_pipeline.corpus_ingest import _content_class_for, classify_format

    fmt = classify_format(analysis, niche_id)
    if fmt:
        video["content_format"] = fmt
    cc = _content_class_for(niche_id, fmt) if fmt else None
    if cc is not None:
        video["content_class_id"] = cc
    return fmt or None


def _has_subtitle_style_overlays(analysis: dict[str, Any]) -> bool:
    for ov in analysis.get("text_overlays") or []:
        if isinstance(ov, dict) and str(ov.get("overlay_style") or "").lower() == "sub_caption":
            return True
    return False


def _format_axis(analysis: dict[str, Any]) -> str:
    nc = analysis.get("niche_classification")
    if isinstance(nc, dict):
        return str(nc.get("format_axis") or "").strip().lower()
    return ""


def detect_foreign_reup(analysis: dict[str, Any]) -> bool:
    """True when the clip is re-uploaded foreign footage with Vietnamese subtitles/dub."""
    tags = {str(t).strip().lower() for t in (analysis.get("style_tags") or []) if t}
    if "foreign_reup" in tags:
        return True

    transcript = str(analysis.get("audio_transcript") or "")
    topics = " ".join(str(t) for t in (analysis.get("topics") or []))
    overlays = _overlay_text_blob(analysis)
    combined = f"{transcript} {topics} {overlays}".lower()

    has_cjk = bool(_CJK_RE.search(transcript) or _CJK_RE.search(overlays))
    has_vn_overlay = bool(_VN_OVERLAY_RE.search(overlays))

    # Primary heuristic: CJK on screen/speech + Vietnamese subtitle layer.
    if has_cjk and has_vn_overlay:
        return True
    # Secondary: strict foreign-origin topics + heavy VN subtitle overlay.
    if (
        _FOREIGN_TOPIC_STRICT_RE.search(combined)
        and has_vn_overlay
        and "text_overlay_heavy" in tags
    ):
        return True
    # Tertiary: react/montage format_axis + CJK without native commerce intent.
    axis = _format_axis(analysis)
    if axis in ("react_commentary", "montage_highlights") and has_cjk:
        if not _commerce_intent_is_commerce(analysis):
            return True
    # Quaternary: VN dub + burned subtitles (no CJK) — CN/KR/JP footage reup pattern.
    has_vn_transcript = bool(_VN_OVERLAY_RE.search(transcript)) and len(transcript.strip()) >= 20
    has_sub_style = _has_subtitle_style_overlays(analysis) or (
        "text_overlay_heavy" in tags and has_vn_overlay
    )
    if (
        has_vn_transcript
        and has_vn_overlay
        and has_sub_style
        and not _commerce_intent_is_commerce(analysis)
        and (
            _FOREIGN_TOPIC_STRICT_RE.search(combined)
            or "voiceover_only" in tags
            or axis in _REUP_FORMAT_AXES
        )
    ):
        return True
    return False


def _format_for_foreign_reup(analysis: dict[str, Any]) -> str:
    nc = analysis.get("niche_classification")
    if isinstance(nc, dict):
        axis = str(nc.get("format_axis") or "").strip().lower()
        mapped = _FORMAT_AXIS_TO_CONTENT_FORMAT.get(axis)
        if mapped == "review" and not _commerce_intent_is_commerce(analysis):
            mapped = "highlight"
        if mapped == "haul" and not _commerce_intent_is_commerce(analysis):
            mapped = "highlight"
        if mapped:
            return mapped
    return "highlight"


def guard_content_format(fmt: str, analysis: dict[str, Any]) -> str:
    """Post-classify correction for foreign reup + weak native commerce FPs."""
    if detect_foreign_reup(analysis) and fmt in _REUP_COMMERCE_FORMATS:
        return _format_for_foreign_reup(analysis)
    if fmt == "haul" and not _commerce_intent_is_commerce(analysis):
        combined = " ".join(
            [
                str(analysis.get("audio_transcript") or "").lower(),
                " ".join(str(t).lower() for t in (analysis.get("topics") or [])),
                _overlay_text_blob(analysis),
            ]
        )
        # Strong unboxing markers still count; weak ``mua…về`` alone does not.
        if re.search(r"haul|đập hộp|unbox|mở hộp", combined):
            return fmt
        if re.search(r"\bmua\b.{0,15}\bvề\b|\bđặt\b.{0,15}\bgửi\b", combined):
            if not re.search(
                r"shopee|tiktok shop|affiliate|sản phẩm|đồ mình mua|đập hộp|unbox|haul",
                combined,
            ):
                return _fallback_after_haul_skip(analysis)
    return fmt


def _fallback_after_haul_skip(analysis: dict[str, Any]) -> str:
    """Re-run is not feasible — return a neutral bucket when weak haul was suppressed."""
    tone = str(analysis.get("tone") or "")
    if tone in ("entertaining", "humorous"):
        return "highlight"
    return "other"


def haul_regex_matches(combined: str, analysis: dict[str, Any], *, is_reup: bool) -> bool:
    """Shared haul matcher for ``classify_format`` — respects reup + commerce gates."""
    if is_reup:
        return False
    if re.search(r"haul|đập hộp|unbox|mở hộp", combined):
        return True
    if re.search(r"\bmua\b.{0,15}\bvề\b|\bđặt\b.{0,15}\bgửi\b", combined):
        if _commerce_intent_is_commerce(analysis):
            return True
        return bool(
            re.search(
                r"shopee|tiktok shop|affiliate|sản phẩm|đồ mình mua",
                combined,
            )
        )
    return False
