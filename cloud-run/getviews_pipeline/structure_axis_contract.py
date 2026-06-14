"""Video structure block — five-axis contract (rhythm / editing / sound / persona / cta).

UI merges ``script_structure`` + ``editing`` + ``sound`` + ``persona`` + ``commerce``
into «Phân tích cấu trúc Video». Each emitted axis must carry prose + actionable findings.
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.diagnose_parse import (
    approximate_word_count_vi,
    count_gap_findings,
    is_positive_fix_vi,
)

# ~2 short sentences in Vietnamese.
STRUCTURE_AXIS_PROSE_MIN_WORDS = 12

_RHYTHM_SECTION = "script_structure"
_EDITING_SECTION = "editing"
_SOUND_SECTION = "sound"
_PERSONA_SECTION = "persona"
_COMMERCE_SECTION = "commerce"

_STRUCTURE_AXIS_SECTIONS = (
    _RHYTHM_SECTION,
    _EDITING_SECTION,
    _SOUND_SECTION,
    _PERSONA_SECTION,
    _COMMERCE_SECTION,
)


def _section_by_id(
    diagnosis_vi: dict[str, Any],
    section_id: str,
) -> dict[str, Any] | None:
    sections = diagnosis_vi.get("sections")
    if not isinstance(sections, list):
        return None
    for raw in sections:
        if isinstance(raw, dict) and str(raw.get("section_id") or "") == section_id:
            return raw
    return None


def _count_strength_findings(sec: dict[str, Any]) -> int:
    findings = sec.get("findings")
    if not isinstance(findings, list):
        return 0
    n = 0
    for f in findings:
        if not isinstance(f, dict):
            continue
        fix = str(f.get("fix_vi") or "").strip()
        if fix and is_positive_fix_vi(fix):
            n += 1
    return n


def _count_actionable_findings(sec: dict[str, Any]) -> int:
    findings = sec.get("findings")
    if not isinstance(findings, list):
        return 0
    n = 0
    for f in findings:
        if not isinstance(f, dict):
            continue
        if str(f.get("fix_vi") or "").strip():
            n += 1
    return n


def _axis_prose_words(sec: dict[str, Any]) -> int:
    raw = sec.get("text_vi") if sec.get("text_vi") is not None else sec.get("text")
    return approximate_word_count_vi(str(raw or ""))


def structure_axis_contract_violations(
    diagnosis_vi: dict[str, Any] | None,
    sections_to_emit: list[str],
) -> list[str]:
    """Return human-readable violation messages (empty list = contract satisfied)."""
    if not diagnosis_vi or not isinstance(diagnosis_vi, dict):
        return ["missing diagnosis_vi"]

    emit = {s for s in sections_to_emit if s in _STRUCTURE_AXIS_SECTIONS}
    if not emit:
        return []

    violations: list[str] = []

    if _RHYTHM_SECTION in emit:
        sec = _section_by_id(diagnosis_vi, _RHYTHM_SECTION)
        if sec is None:
            violations.append("script_structure: section missing")
        else:
            prose_w = _axis_prose_words(sec)
            if prose_w < STRUCTURE_AXIS_PROSE_MIN_WORDS:
                violations.append(
                    f"script_structure: prose too short ({prose_w}<{STRUCTURE_AXIS_PROSE_MIN_WORDS} words)"
                )
            if _count_strength_findings(sec) < 1:
                violations.append("script_structure: need ≥1 strength finding (fix_vi Tiếp tục/Giữ)")
            gaps = count_gap_findings(sec)
            if gaps < 1:
                violations.append("script_structure: need ≥1 gap finding with corrective fix_vi")
            else:
                tiles = sec.get("embedded_tiles")
                tile_n = len(tiles) if isinstance(tiles, list) else 0
                if tile_n < gaps:
                    violations.append(
                        f"script_structure: need ≥1 embedded_tile per gap "
                        f"(gaps={gaps}, tiles={tile_n})"
                    )

    if _EDITING_SECTION in emit:
        sec = _section_by_id(diagnosis_vi, _EDITING_SECTION)
        if sec is None:
            violations.append("editing: section missing")
        else:
            prose_w = _axis_prose_words(sec)
            if prose_w < STRUCTURE_AXIS_PROSE_MIN_WORDS:
                violations.append(
                    f"editing: prose too short ({prose_w}<{STRUCTURE_AXIS_PROSE_MIN_WORDS} words)"
                )
            if _count_actionable_findings(sec) < 1:
                violations.append("editing: need ≥1 finding with fix_vi")

    if _SOUND_SECTION in emit:
        sec = _section_by_id(diagnosis_vi, _SOUND_SECTION)
        if sec is None:
            violations.append("sound: section missing")
        else:
            prose_w = _axis_prose_words(sec)
            if prose_w < STRUCTURE_AXIS_PROSE_MIN_WORDS:
                violations.append(
                    f"sound: prose too short ({prose_w}<{STRUCTURE_AXIS_PROSE_MIN_WORDS} words)"
                )
            if _count_actionable_findings(sec) < 1:
                violations.append("sound: need ≥1 finding with fix_vi")

    if _PERSONA_SECTION in emit:
        sec = _section_by_id(diagnosis_vi, _PERSONA_SECTION)
        if sec is None:
            violations.append("persona: section missing")
        else:
            prose_w = _axis_prose_words(sec)
            if prose_w < STRUCTURE_AXIS_PROSE_MIN_WORDS:
                violations.append(
                    f"persona: prose too short ({prose_w}<{STRUCTURE_AXIS_PROSE_MIN_WORDS} words)"
                )
            if _count_actionable_findings(sec) < 1:
                violations.append("persona: need ≥1 finding with fix_vi")

    if _COMMERCE_SECTION in emit:
        sec = _section_by_id(diagnosis_vi, _COMMERCE_SECTION)
        if sec is None:
            violations.append("commerce: section missing")
        else:
            prose_w = _axis_prose_words(sec)
            if prose_w < STRUCTURE_AXIS_PROSE_MIN_WORDS:
                violations.append(
                    f"commerce: prose too short ({prose_w}<{STRUCTURE_AXIS_PROSE_MIN_WORDS} words)"
                )
            if _count_actionable_findings(sec) < 1:
                violations.append("commerce: need ≥1 finding with fix_vi")

    return violations


def build_structure_axis_retry_append(violations: list[str]) -> str:
    if not violations:
        return ""
    bullet = "\n".join(f"- {v}" for v in violations)
    return (
        "\n\nBẮT BUỘC SỬA TRỤC CẤU TRÚC (lần retry): Block «Phân tích cấu trúc Video» gồm "
        "5 trục riêng trên UI — mỗi section BE phải đủ prose + findings:\n"
        f"{bullet}\n"
        "- script_structure (Nhịp & cắt): section.text 2-4 câu (≤120 từ) + 1 điểm mạnh "
        "+ 1-2 thiếu sót nhịp/cảnh/cách quay + embedded_tiles (≥1 tile / thiếu sót).\n"
        "- editing (Hậu kỳ & hình): section.text 2-3 câu (≤55 từ) về color grade, chữ overlay, "
        "cách quay/hậu kỳ — KHÔNG để trống khi editing có trong SECTIONS_TO_EMIT.\n"
        "- sound (Âm thanh): section.text 2-3 câu (≤55 từ) + ≥1 finding âm thanh — "
        "KHÔNG để text trống khi sound có trong SECTIONS_TO_EMIT.\n"
        "- persona (Giọng & persona): section.text 2-3 câu (≤55 từ) + ≥1 finding giọng/"
        "chân thực — KHÔNG để text trống khi persona có trong SECTIONS_TO_EMIT.\n"
        "- commerce (Kêu gọi hành động): section.text 2-3 câu (≤55 từ) + ≥1 finding CTA "
        "giọng/caption/link — KHÔNG để text trống khi commerce có trong SECTIONS_TO_EMIT.\n"
        "Giữ schema JSON; chỉ bổ sung/sửa các section trên."
    )
