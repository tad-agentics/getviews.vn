"""§7 Share/save triggers + 'sự thật trần trụi' trust pattern — diagnosis signals (Sprint 7)."""

from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal

_SU_THAT_TRAN_TRUI_RES = (
    re.compile(
        r"thử\s+[^,.;]{0,56}\s*(nhưng|thì|mà)\s*(thất\s*vọng|hối\s*hận|tệ|dở|phí|lừa|fail)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(đã|đã\s+từng)\s+dùng\s+[^,.;]{0,48}\s*(nhưng|mà|thì)\s*(thất|tệ|dở|không|chán)",
        re.IGNORECASE,
    ),
    re.compile(
        r"không\s+(đúng|giống)\s+(quảng\s*cáo|qc|review|clip\s*quảng\s*cáo)",
        re.IGNORECASE,
    ),
    re.compile(
        r"trải\s*nghiệm\s*thật[^,.;]{0,20}(thất\s*vọng|tệ|dở| không\s*OK)",
        re.IGNORECASE,
    ),
)


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis") or {}
    return ua if isinstance(ua, dict) else {}


def extract_su_that_tran_trui_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    tr = str(ua.get("audio_transcript") or "")
    if len(tr.strip()) < 12:
        return []
    if not any(r.search(tr) for r in _SU_THAT_TRAN_TRUI_RES):
        return []
    return [
        Signal(
            id="trigger_su_that_tran_trui",
            section_id="diagnosis",
            taxonomy_ref="§7",
            salience=0.65,
            claim=(
                "Có dấu hiệu 'sự thật trần trụi' (thử rồi thất vọng / không như quảng cáo) "
                "— mô típ tăng tin cậy nếu khớp bằng chứng trên clip."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote="audio_transcript matches su_than tran trui heuristic",
                    location="user_analysis.audio_transcript",
                ),
            ],
            suggested_fix="Giữ ngôn ngữ cụ thể + clip minh chứng (trước/sau) để tránh bị đọc là drama ảo.",
        )
    ]


def extract_share_trigger_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    raw = ua.get("share_trigger_type")
    st = str(raw or "").strip().lower()
    if not st or st in ("none", "null"):
        return []
    return [
        Signal(
            id="trigger_share_archetype",
            section_id="diagnosis",
            taxonomy_ref="§7",
            salience=0.4,
            claim=f"Kích thích chia sẻ chủ đạo: {st} — dùng để khớp format với niche.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"share_trigger_type={st}",
                    location="user_analysis.share_trigger_type",
                ),
            ],
            suggested_fix=None,
        )
    ]


def extract_save_trigger_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    raw = ua.get("save_trigger_type")
    sv = str(raw or "").strip().lower()
    if not sv or sv in ("none", "null"):
        return []
    return [
        Signal(
            id="trigger_save_archetype",
            section_id="diagnosis",
            taxonomy_ref="§7",
            salience=0.4,
            claim=f"Kích thích lưu chủ đạo: {sv} — hữu ích cho packaging caption/overlay.",
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"save_trigger_type={sv}",
                    location="user_analysis.save_trigger_type",
                ),
            ],
            suggested_fix=None,
        )
    ]


def extract_trigger_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_su_that_tran_trui_signal(ctx))
    out.extend(extract_share_trigger_signal(ctx))
    out.extend(extract_save_trigger_signal(ctx))
    return out
