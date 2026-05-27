"""TikTok / TikTok Shop policy scans — restricted phrases, safe zone, off-platform, neo giá."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# (phrase, category, severity) — conservative substring scan on VO/caption/overlays.
RESTRICTED_VI_PHRASES: tuple[tuple[str, str, str], ...] = (
    # Health / misleading claims (Community Guidelines + VN ad law context)
    ("cam kết khỏi hẳn", "health_claim", "high"),
    ("trị dứt điểm", "health_claim", "high"),
    ("100% hiệu quả", "health_claim", "high"),
    ("chữa trị", "health_claim", "medium"),
    ("trị dứt điểm mụn", "health_claim", "high"),
    ("tuyệt đối an toàn", "health_claim", "medium"),
    ("không tác dụng phụ", "health_claim", "medium"),
    # Price guarantees / Shop misleading pricing
    ("giá rẻ nhất thị trường", "price_guarantee", "high"),
    ("cam kết hoàn tiền 100%", "price_guarantee", "high"),
    ("giá thấp nhất", "price_guarantee", "medium"),
    # Off-platform diversion (anti-spam / integrity)
    ("add zalo", "off_platform", "high"),
    ("nhắn zalo", "off_platform", "high"),
    ("ib zalo", "off_platform", "high"),
    ("inbox facebook", "off_platform", "high"),
    ("inbox instagram", "off_platform", "high"),
    ("link youtube", "off_platform", "medium"),
    ("telegram", "off_platform", "medium"),
    ("whatsapp", "off_platform", "medium"),
    ("mua ngoài tiktok", "off_platform", "high"),
    # Violence / shock (distribution throttle risk)
    ("máu me", "violence", "high"),
    ("chém chết", "violence", "high"),
    ("tự tử", "violence", "high"),
)

# Hashtag substrings often tied to spam/engagement bait policies (caption only).
RISKY_HASHTAG_SNIPPETS: tuple[tuple[str, str, str], ...] = (
    ("follow4follow", "engagement_bait", "medium"),
    ("f4f", "engagement_bait", "medium"),
    ("comment4comment", "engagement_bait", "medium"),
    ("sub4sub", "engagement_bait", "medium"),
)

_HASHTAG_RE = re.compile(
    r"#([\wĐđàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+)",
    re.UNICODE,
)

_K_AMOUNT_RE = re.compile(
    r"(?:(\d{1,3}(?:[.,]\d{3})+)|(\d+))\s*k\b",
    re.IGNORECASE | re.UNICODE,
)

# Caption/overlay hints that count as AI/synthetic disclosure (§10).
_AI_DISCLOSURE_SNIPPETS: tuple[str, ...] = (
    "#aigenerated",
    "#ai_generated",
    "#synthetic",
    "tạo bằng ai",
    "tao bang ai",
    "nội dung ai",
    "noi dung ai",
    "synthetic media",
    "ai-generated",
    "nhãn ai",
    "nhan ai",
    "công nghệ ai",
    "cong nghe ai",
)


def _normalize_text(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


def _overlay_texts(user_analysis: dict[str, Any]) -> list[str]:
    raw = user_analysis.get("text_overlays") or []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for o in raw:
        if isinstance(o, dict):
            t = str(o.get("text") or "")
        else:
            t = str(o)
        if t.strip():
            out.append(t)
    return out


def _haystacks(
    user_analysis: dict[str, Any], user_stats: dict[str, Any]
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    tr = str(user_analysis.get("audio_transcript") or "")
    if tr.strip():
        out.append((tr, "audio_transcript"))
    cap = str(user_stats.get("caption") or "")
    if cap.strip():
        out.append((cap, "caption"))
    for i, t in enumerate(_overlay_texts(user_analysis)):
        out.append((t, f"text_overlays[{i}]"))
    return out


def scan_restricted_phrases(
    user_analysis: dict[str, Any], user_stats: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return structured flags for each restricted-phrase hit."""
    flags: list[dict[str, Any]] = []
    for text, location in _haystacks(user_analysis, user_stats):
        n = _normalize_text(text)
        for phrase, category, severity in RESTRICTED_VI_PHRASES:
            if _normalize_text(phrase) in n:
                flags.append(
                    {
                        "phrase": phrase,
                        "location": location,
                        "severity": severity,
                        "category": category,
                    }
                )
    return flags


def scan_risky_hashtags(user_stats: dict[str, Any]) -> list[dict[str, Any]]:
    """Engagement-bait hashtag patterns in caption (TikTok spam policies)."""
    cap = str(user_stats.get("caption") or "")
    if not cap.strip():
        return []
    n = _normalize_text(cap)
    flags: list[dict[str, Any]] = []
    for tag, category, severity in RISKY_HASHTAG_SNIPPETS:
        if _normalize_text(tag) in n:
            flags.append(
                {
                    "phrase": f"#{tag}",
                    "location": "caption",
                    "severity": severity,
                    "category": category,
                }
            )
    for m in _HASHTAG_RE.finditer(cap):
        tag = m.group(1)
        if tag and len(tag) <= 2 and tag.isascii():
            flags.append(
                {
                    "phrase": f"#{tag}",
                    "location": "caption",
                    "severity": "low",
                    "category": "hashtag_noise",
                }
            )
    return flags


def scan_safe_zone_violation(user_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """TikTok UI safe zone — CTA/price in bottom ~35% (Shop cart overlap)."""
    raw = user_analysis.get("safe_zone_status")
    if str(raw or "").strip().lower() != "bottom_overlay_risk":
        return []
    return [
        {
            "phrase": "Chữ hoặc CTA nằm vùng dưới khung (che UI Shop/giỏ)",
            "location": "safe_zone_status",
            "severity": "high",
            "category": "safe_zone",
        }
    ]


def _k_values_vnd(normalized_blob: str) -> list[int]:
    """Extract `Nk` style amounts → integer VND (×1000)."""
    vals: list[int] = []
    for m in _K_AMOUNT_RE.finditer(normalized_blob):
        raw = (m.group(1) or m.group(2) or "").replace(".", "").replace(",", "")
        try:
            k = int(raw)
        except ValueError:
            continue
        if k > 0:
            vals.append(k * 1000)
    return vals


def scan_inflated_price_anchor(
    user_analysis: dict[str, Any], user_stats: dict[str, Any]
) -> list[dict[str, Any]]:
    """Heuristic: two k-suffix prices in VO/caption/overlays with anchor ≥5× sale."""
    chunks: list[str] = []
    for text, _loc in _haystacks(user_analysis, user_stats):
        chunks.append(text)
    blob = " ".join(chunks)
    n = _normalize_text(blob)
    vals = sorted(set(_k_values_vnd(n)), reverse=True)
    if len(vals) < 2:
        return []
    hi, lo = vals[0], vals[-1]
    if lo < 20_000 or hi < 50_000:
        return []
    if lo <= 0 or hi < lo * 5:
        return []
    return [
        {
            "phrase": f"neo giá ~{hi // 1000}k vs giá chào ~{lo // 1000}k (≥5×)",
            "location": "price_anchor_numeric",
            "severity": "high",
            "category": "price_anchor_inflated",
        }
    ]


def _text_has_ai_disclosure_hint(
    user_analysis: dict[str, Any], user_stats: dict[str, Any]
) -> bool:
    for text, _loc in _haystacks(user_analysis, user_stats):
        n = _normalize_text(text)
        for snippet in _AI_DISCLOSURE_SNIPPETS:
            if _normalize_text(snippet) in n:
                return True
    return False


def scan_ai_disclosure_gap(
    user_analysis: dict[str, Any], user_stats: dict[str, Any]
) -> list[dict[str, Any]]:
    """§10 — suspected AI/synthetic footage without TikTok/Meta-required label."""
    if user_analysis.get("ai_generated_suspected") is not True:
        return []
    if user_analysis.get("ai_disclosure_present") is True:
        return []
    if _text_has_ai_disclosure_hint(user_analysis, user_stats):
        return []
    return [
        {
            "phrase": "Nội dung nghi AI/synthetic nhưng thiếu nhãn tiết lộ",
            "location": "user_analysis.ai_disclosure_present",
            "severity": "high",
            "category": "ai_disclosure",
        }
    ]


def collect_compliance_flags(
    user_analysis: dict[str, Any] | None, user_stats: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Aggregate TikTok policy scan results for diagnosis ctx + compliance section."""
    ua = user_analysis if isinstance(user_analysis, dict) else {}
    st = user_stats if isinstance(user_stats, dict) else {}
    flags = scan_restricted_phrases(ua, st)
    flags.extend(scan_inflated_price_anchor(ua, st))
    flags.extend(scan_risky_hashtags(st))
    flags.extend(scan_safe_zone_violation(ua))
    flags.extend(scan_ai_disclosure_gap(ua, st))
    return flags
