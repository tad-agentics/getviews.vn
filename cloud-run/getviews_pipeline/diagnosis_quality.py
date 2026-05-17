from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.diagnose_parse import approximate_word_count_vi


def score_diagnosis_output_v6(
    diagnosis_vi: dict[str, Any] | None,
    *,
    section_ids_expected: list[str] | None = None,
) -> dict[str, Any]:
    """Heuristic QA scores for v6 JSON (no LLM call). Returns component 0–1 scores."""
    out: dict[str, Any] = {
        "evidence_integrity_ratio": None,
        "section_depth_ok_ratio": None,
        "section_discipline": None,
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

    depths = [
        approximate_word_count_vi(str(s.get("text") or ""))
        for s in sections
        if isinstance(s, dict) and str(s.get("section_id")) != "next_video"
    ]
    if depths:
        ok = sum(1 for d in depths if d >= 200) / len(depths)
    else:
        ok = 0.0

    bullet_violation = bool(re.search(r"^\s*[-*•]\s+", body, re.MULTILINE))

    return {
        **out,
        "valid": True,
        "evidence_integrity_ratio": round(evidence_integrity_ratio, 4),
        "section_depth_ok_ratio": round(ok, 4),
        "section_discipline": section_discipline,
        "bullet_line_violation": bullet_violation,
    }
