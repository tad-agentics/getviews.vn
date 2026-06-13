"""Structure axis contract — rhythm / editing / sound / persona completeness."""

from __future__ import annotations

from getviews_pipeline.structure_axis_contract import (
    STRUCTURE_AXIS_PROSE_MIN_WORDS,
    build_structure_axis_retry_append,
    structure_axis_contract_violations,
)


def _rhythm_section(*, text: str, strength: bool = True, gap: bool = True) -> dict:
    findings = []
    if strength:
        findings.append({"title_vi": "Nhịp nhanh", "fix_vi": "Tiếp tục giữ nhịp cắt 1,2s."})
    if gap:
        findings.append({"title_vi": "Dead air", "fix_vi": "Xen cận mỗi 2 giây."})
    sec: dict = {"section_id": "script_structure", "text": text, "findings": findings}
    if gap:
        sec["embedded_tiles"] = [{"aweme_id": "111", "narrative_vi": "Peer xen cận đúng nhịp."}]
    return sec


def _sound_section(*, text: str) -> dict:
    return {
        "section_id": "sound",
        "text": text,
        "findings": [{"title_vi": "VO mỏng", "fix_vi": "Tăng volume voiceover 20%."}],
    }


def _persona_section(*, text: str) -> dict:
    return {
        "section_id": "persona",
        "text": text,
        "findings": [{"title_vi": "Thiếu chân thực", "fix_vi": "Thêm chi tiết tiêu cực."}],
    }


def _editing_section(*, text: str) -> dict:
    return {
        "section_id": "editing",
        "text": text,
        "findings": [{"title_vi": "Chữ nhỏ", "fix_vi": "Tăng font overlay lên 48px."}],
    }


def test_contract_passes_when_all_axes_complete() -> None:
    prose = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            _rhythm_section(text=prose),
            _editing_section(text=prose),
            _sound_section(text=prose),
            _persona_section(text=prose),
        ]
    }
    assert structure_axis_contract_violations(
        diag,
        ["script_structure", "editing", "sound", "persona"],
    ) == []


def test_contract_passes_when_rhythm_sound_persona_only() -> None:
    prose = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            _rhythm_section(text=prose),
            _sound_section(text=prose),
            _persona_section(text=prose),
        ]
    }
    assert structure_axis_contract_violations(
        diag,
        ["script_structure", "sound", "persona"],
    ) == []


def test_contract_flags_missing_editing_prose() -> None:
    prose = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            _rhythm_section(text=prose),
            {"section_id": "editing", "text": "ngắn", "findings": []},
        ]
    }
    violations = structure_axis_contract_violations(diag, ["script_structure", "editing"])
    assert any("editing: prose too short" in v for v in violations)
    assert any("editing: need" in v for v in violations)


def test_contract_flags_missing_sound_prose() -> None:
    prose = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            _rhythm_section(text=prose),
            {"section_id": "sound", "text": "ngắn", "findings": []},
        ]
    }
    violations = structure_axis_contract_violations(diag, ["script_structure", "sound"])
    assert any("sound: prose too short" in v for v in violations)
    assert any("sound: need" in v for v in violations)


def test_contract_flags_missing_rhythm_strength() -> None:
    prose = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            _rhythm_section(text=prose, strength=False, gap=True),
        ]
    }
    violations = structure_axis_contract_violations(diag, ["script_structure"])
    assert any("script_structure: need ≥1 strength" in v for v in violations)


def test_contract_reads_text_vi_for_prose_length() -> None:
    short = " ".join(["câu"] * 3)
    long = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            {
                "section_id": "sound",
                "text": short,
                "text_vi": long,
                "findings": [{"title_vi": "VO mỏng", "fix_vi": "Tăng volume voiceover 20%."}],
            },
        ]
    }
    violations = structure_axis_contract_violations(diag, ["sound"])
    assert not any("prose too short" in v for v in violations)


def test_contract_flags_missing_peer_tiles_for_rhythm_gaps() -> None:
    prose = " ".join(["câu"] * STRUCTURE_AXIS_PROSE_MIN_WORDS)
    diag = {
        "sections": [
            {
                "section_id": "script_structure",
                "text": prose,
                "findings": [
                    {"title_vi": "Nhịp nhanh", "fix_vi": "Tiếp tục giữ nhịp cắt 1,2s."},
                    {"title_vi": "Dead air", "fix_vi": "Xen cận mỗi 2 giây."},
                ],
                "embedded_tiles": [],
            },
        ]
    }
    violations = structure_axis_contract_violations(diag, ["script_structure"])
    assert any("embedded_tile per gap" in v for v in violations)


def test_retry_append_lists_violations() -> None:
    append = build_structure_axis_retry_append(["sound: section missing"])
    assert "sound (Âm thanh)" in append
    assert "editing (Hậu kỳ & hình)" in append
    assert "sound: section missing" in append
