"""§11 Vietnamese on-camera persona + slang — diagnosis signals (Sprint 3)."""

from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_NEGATIVE_EXPERIENCE_RE = re.compile(
    r"thất\s*vọng|tệ\s*quá|không\s*hiệu\s*quả|phí\s*tiền|hối\s*hận|"
    r"\btoang\b|fail|dở\s*tệ|lừa\s*đảo|vô\s*dụng|kinh\s*dị",
    re.IGNORECASE,
)

_REGIONALDialect_HOOK = frozenset({"hue", "quang_nam", "southern", "northern"})
_EXPERT_LIKE_PERSONAS = frozenset({"chuyen_gia", "anh_chi_mentor"})
_MIN_NICHE_SAMPLE_TONE = 30


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis") or {}
    return ua if isinstance(ua, dict) else {}


def extract_persona_mismatch_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    ch = ctx.get("channel_context") or {}
    if not isinstance(ch, dict) or not ch.get("available"):
        return []
    base = str(ch.get("dominant_creator_persona") or "").strip().lower().replace("-", "_")
    cur = str(ua.get("creator_persona") or "").strip().lower().replace("-", "_")
    if not base or not cur or base == cur:
        return []
    return [
        Signal(
            id="persona_channel_baseline_mismatch",
            section_id="persona",
            taxonomy_ref="§11",
            salience=0.65,
            claim=(
                f"Persona clip ({cur}) lệch với pattern gần đây trên kênh ({base}) "
                f"— có thể là pivot hoặc thử nghiệm chưa ổn định."
            ),
            evidence=[
                Evidence(
                    type="channel_field",
                    quote=f"creator_persona={cur} dominant_creator_persona={base}",
                    location="user_analysis.creator_persona+channel_context",
                )
            ],
            suggested_fix="Thống nhất vai hoặc tách rõ lý do đổi persona để khán giả không rối.",
        )
    ]


def extract_persona_authenticity_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    cp = str(ua.get("creator_persona") or "").strip().lower().replace("-", "_")
    if cp != "nguoi_trai_nghiem_that":
        return []
    tr = str(ua.get("audio_transcript") or "")
    if _NEGATIVE_EXPERIENCE_RE.search(tr):
        return []
    return [
        Signal(
            id="persona_authenticity_weak_negative_markers",
            section_id="persona",
            taxonomy_ref="§11",
            salience=0.7,
            claim=(
                "Tự nhận 'trải nghiệm thật' nhưng thoại thiếu dấu hiệu tiêu cực / va chạm — "
                "dễ bị đọc là dàn dựng."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="creator_persona=nguoi_trai_nghiem_that (no negative markers in transcript)",
                    location="user_analysis.audio_transcript",
                )
            ],
            suggested_fix="Thêm một chi tiết trải nghiệm có ma sát (lỗi, rủi ro, cảm xúc) nếu đúng là review thật.",
        )
    ]


def extract_slang_freshness_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    tier = str(ua.get("slang_freshness_score") or "").strip().lower().replace("-", "_")
    if tier != "dated":
        return []
    terms = ua.get("slang_terms_used") or []
    tail = ", ".join(str(t) for t in terms[:4]) if isinstance(terms, list) else ""
    return [
        Signal(
            id="persona_slang_dated",
            section_id="persona",
            taxonomy_ref="§11",
            salience=0.45,
            claim="Slang trong clip có dấu hiệu lỗi thời — rủi ro 'không còn hot' với Gen Z.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"slang_freshness_score=dated terms=[{tail}]",
                    location="user_analysis.slang_terms_used",
                )
            ],
            suggested_fix="Cập nhật cụm viral trong quý hoặc giảm phụ thuộc trend chữ.",
        )
    ]


def extract_dialect_persona_consistency_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    cp = str(ua.get("creator_persona") or "").strip().lower().replace("-", "_")
    if cp not in _EXPERT_LIKE_PERSONAS:
        return []
    ha = ua.get("hook_analysis") if isinstance(ua.get("hook_analysis"), dict) else {}
    d = str(ha.get("dialect_detected") or "").strip().lower().replace("-", "_")
    if d not in _REGIONALDialect_HOOK:
        return []
    return [
        Signal(
            id="persona_dialect_expert_tension",
            section_id="persona",
            taxonomy_ref="§11",
            salience=0.6,
            claim=(
                "Giọng/địa phương lộ rõ trong hook trong khi persona đang là chuyên gia/mentor — "
                "có thể là điểm mạnh hoặc lệch kỳ vọng 'chuyên gia trung lập'."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"creator_persona={cp} dialect_detected={d}",
                    location="user_analysis.hook_analysis.dialect_detected",
                )
            ],
            suggested_fix="Chủ đích hoá địa phương hoặc neutral hoá nếu muốn thuyết phục rộng.",
        )
    ]


def extract_tone_distribution_gap_signal(ctx: dict) -> list[Signal]:
    """P1 — tone lệch tone_distribution ngách."""
    nm = ctx.get("niche_meta") or {}
    if not isinstance(nm, dict):
        return []
    dist = nm.get("tone_distribution")
    if not isinstance(dist, dict) or not dist:
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < _MIN_NICHE_SAMPLE_TONE:
        return []

    total = sum(int(v or 0) for v in dist.values())
    if total <= 0:
        return []

    ua = _ua(ctx)
    tone = str(ua.get("tone") or "").strip().lower().replace("-", "_")
    if not tone or tone in ("none", "unknown", "other"):
        return []

    tone_count = int(dist.get(tone) or dist.get(tone.replace("_", "-")) or 0)
    percentile = round(100 * tone_count / total)
    if percentile >= 12:
        return []

    return [
        Signal(
            id="persona_tone_distribution_gap",
            section_id="persona",
            taxonomy_ref="§11",
            salience=0.62,
            claim=(
                f"Tone `{tone}` chỉ ~{percentile}% corpus ngách — "
                "có dấu hiệu lệch mood đang tích lũy view."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"tone={tone} niche_tone_share={percentile}%",
                    location="user_analysis.tone+niche_meta.tone_distribution",
                )
            ],
            suggested_fix="Thử tone thuộc top 2 distribution hoặc tách biệt rõ chủ đích.",
        )
    ]


def extract_persona_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_persona_mismatch_signal(ctx))
    out.extend(extract_persona_authenticity_signal(ctx))
    out.extend(extract_slang_freshness_signal(ctx))
    out.extend(extract_dialect_persona_consistency_signal(ctx))
    out.extend(extract_tone_distribution_gap_signal(ctx))
    return out
