from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.diagnose_parse import approximate_word_count_vi

# Report redesign 2026-05 — prompt targets; retry uses soft ceiling.
# Aligned with diagnose_prompts.py section.text cap (≤90 từ, 2026-06-12).
DIAGNOSIS_V6_SECTION_MAX_WORDS = 90
DIAGNOSIS_V6_SECTION_SOFT_MAX = 95
DIAGNOSIS_V6_SCRIPT_STRUCTURE_MAX_WORDS = 100
DIAGNOSIS_V6_SCRIPT_STRUCTURE_SOFT_MAX = 105
DIAGNOSIS_V6_SOUND_PERSONA_MAX_WORDS = 55
DIAGNOSIS_V6_SOUND_PERSONA_SOFT_MAX = 60
DIAGNOSIS_V6_TOTAL_TARGET_MAX = 450
DIAGNOSIS_V6_TOTAL_RETRY_MAX = 520
DIAGNOSIS_V6_NEXT_VIDEO_MAX_WORDS = 150


def _section_text_soft_max(section_id: str) -> int:
    if section_id == "script_structure":
        return DIAGNOSIS_V6_SCRIPT_STRUCTURE_SOFT_MAX
    if section_id in ("sound", "persona", "editing"):
        return DIAGNOSIS_V6_SOUND_PERSONA_SOFT_MAX
    if section_id == "next_video":
        return DIAGNOSIS_V6_NEXT_VIDEO_MAX_WORDS
    return DIAGNOSIS_V6_SECTION_SOFT_MAX


def _section_prose_words(section: dict[str, Any]) -> int:
    raw = section.get("text_vi") if section.get("text_vi") is not None else section.get("text")
    total = approximate_word_count_vi(str(raw or ""))
    findings = section.get("findings")
    if isinstance(findings, list):
        for f in findings:
            if not isinstance(f, dict):
                continue
            for key in ("title_vi", "body_vi", "fix_vi"):
                total += approximate_word_count_vi(str(f.get(key) or ""))
    return total


def diagnosis_v6_word_counts(diagnosis_vi: dict[str, Any] | None) -> dict[str, Any]:
    """Per-section and total word counts for v6 diagnosis_vi."""
    if not diagnosis_vi or not isinstance(diagnosis_vi, dict):
        return {"total": 0, "by_section": {}, "valid": False}

    sections = diagnosis_vi.get("sections") or []
    if not isinstance(sections, list):
        return {"total": 0, "by_section": {}, "valid": False}

    by_section: dict[str, int] = {}
    total = 0
    for s in sections:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("section_id") or "")
        w = _section_prose_words(s)
        by_section[sid] = w
        total += w

    return {"total": total, "by_section": by_section, "valid": True}


def diagnosis_v6_word_budget_exceeded(diagnosis_vi: dict[str, Any] | None) -> bool:
    """True when synthesis exceeds redesign length caps (triggers one shorten retry)."""
    counts = diagnosis_v6_word_counts(diagnosis_vi)
    if not counts.get("valid"):
        return False

    if int(counts["total"]) > DIAGNOSIS_V6_TOTAL_RETRY_MAX:
        return True

    for s in (diagnosis_vi or {}).get("sections") or []:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("section_id") or "")
        raw = s.get("text_vi") if s.get("text_vi") is not None else s.get("text")
        text_w = approximate_word_count_vi(str(raw or ""))
        if text_w > _section_text_soft_max(sid):
            return True

    return False


def score_diagnosis_output_v6(
    diagnosis_vi: dict[str, Any] | None,
    *,
    section_ids_expected: list[str] | None = None,
) -> dict[str, Any]:
    """Heuristic QA scores for v6 JSON (no LLM call). Returns component 0–1 scores."""
    out: dict[str, Any] = {
        "evidence_integrity_ratio": None,
        "section_brevity_ok_ratio": None,
        "section_discipline": None,
        "total_word_count": None,
        "word_budget_ok": None,
        "signals_note": "signal_coverage needs manifest — run offline compare",
    }
    if not diagnosis_vi or not isinstance(diagnosis_vi, dict):
        return {**out, "valid": False, "reason": "missing diagnosis_vi"}

    sections = diagnosis_vi.get("sections") or []
    anchors = diagnosis_vi.get("evidence_anchors") or []
    if not isinstance(sections, list):
        return {**out, "valid": False, "reason": "sections not list"}

    id_set = {str(s.get("section_id") or "") for s in sections if isinstance(s, dict)}
    if section_ids_expected:
        exp = [x for x in section_ids_expected if x]
        section_discipline = 1.0 if id_set == set(exp) else 0.0
    else:
        section_discipline = 1.0 if id_set else 0.0

    body = "\n".join(
        str(s.get("text") or "") for s in sections if isinstance(s, dict)
    )
    sentences = [
        p.strip()
        for p in re.split(r"(?<=[.!?])\s+", body)
        if len(p.strip()) > 10
    ]
    n_sent = max(1, len(sentences))
    anchor_n = len(anchors) if isinstance(anchors, list) else 0
    evidence_integrity_ratio = min(1.0, anchor_n / max(1, int(n_sent * 0.6)))

    brevity_checks: list[bool] = []
    for s in sections:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("section_id") or "")
        raw = s.get("text_vi") if s.get("text_vi") is not None else s.get("text")
        text_w = approximate_word_count_vi(str(raw or ""))
        brevity_checks.append(text_w <= _section_text_soft_max(sid))

    section_brevity_ok_ratio = (
        sum(1 for ok in brevity_checks if ok) / len(brevity_checks) if brevity_checks else 0.0
    )

    wc = diagnosis_v6_word_counts(diagnosis_vi)
    total_words = int(wc.get("total") or 0)
    word_budget_ok = not diagnosis_v6_word_budget_exceeded(diagnosis_vi)

    bullet_violation = bool(re.search(r"^\s*[-*•]\s+", body, re.MULTILINE))

    return {
        **out,
        "valid": True,
        "evidence_integrity_ratio": round(evidence_integrity_ratio, 4),
        "section_brevity_ok_ratio": round(section_brevity_ok_ratio, 4),
        "section_discipline": section_discipline,
        "total_word_count": total_words,
        "word_budget_ok": word_budget_ok,
        "bullet_line_violation": bullet_violation,
    }
