"""§10 Vietnam platform compliance helpers — restricted phrases + price-anchor scan."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# (phrase, category, severity) — taxonomy §10; scan is conservative (substring).
RESTRICTED_VI_PHRASES: tuple[tuple[str, str, str], ...] = (
    ("cam kết khỏi hẳn", "health_claim", "high"),
    ("trị dứt điểm", "health_claim", "high"),
    ("100% hiệu quả", "health_claim", "high"),
    ("chữa trị", "health_claim", "medium"),
    ("trị dứt điểm mụn", "health_claim", "high"),
    ("giá rẻ nhất thị trường", "price_guarantee", "high"),
    ("cam kết hoàn tiền 100%", "price_guarantee", "high"),
    ("add zalo", "off_platform", "high"),
    ("inbox facebook", "off_platform", "high"),
    ("link youtube", "off_platform", "medium"),
)

_K_AMOUNT_RE = re.compile(
    r"(\d{1,3}(?:[.,]\d{3})*)\s*k\b",
    re.IGNORECASE | re.UNICODE,
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


def _k_values_vnd(normalized_blob: str) -> list[int]:
    """Extract `Nk` style amounts → integer VND (×1000)."""
    vals: list[int] = []
    for m in _K_AMOUNT_RE.finditer(normalized_blob):
        raw = m.group(1).replace(".", "").replace(",", "")
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


def collect_compliance_flags(
    user_analysis: dict[str, Any] | None, user_stats: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Aggregate §10 scan results for diagnosis ctx + compliance section."""
    ua = user_analysis if isinstance(user_analysis, dict) else {}
    st = user_stats if isinstance(user_stats, dict) else {}
    flags = scan_restricted_phrases(ua, st)
    flags.extend(scan_inflated_price_anchor(ua, st))
    return flags
