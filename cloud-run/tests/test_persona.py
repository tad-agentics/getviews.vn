"""Unit tests for persona slot extraction (P2-1).

The prod bug this guards against: user wrote "target khách hàng 18-25 tuổi"
and the response never mentioned the age range. extract_persona_slots() must
surface that so the synthesis prompt can require the model to address it.
"""

from __future__ import annotations

from getviews_pipeline.persona import (
    build_persona_block,
    extract_persona_slots,
)


def test_extracts_age_range() -> None:
    slots = extract_persona_slots("target khách hàng 18-25 tuổi")
    assert slots.audience_age == "18-25"


def test_extracts_age_range_with_en_dash() -> None:
    slots = extract_persona_slots("phù hợp cho 18–25 tuổi")
    assert slots.audience_age == "18-25"


def test_extracts_single_age() -> None:
    slots = extract_persona_slots("dành cho người 25 tuổi trở lên")
    assert slots.audience_age == "25"


def test_extracts_cohort_gen_z() -> None:
    slots = extract_persona_slots("content hợp gu gen Z hiện nay")
    assert slots.audience_cohort == "gen Z"


def test_extracts_multiple_pain_points() -> None:
    slots = extract_persona_slots(
        "review đồ skincare Hàn Quốc cho da dầu mụn, target khách hàng 18-25 tuổi"
    )
    assert "da dầu" in slots.pain_points
    assert "mụn" in slots.pain_points
    assert slots.geography == "Hàn Quốc"
    assert slots.audience_age == "18-25"


def test_empty_query_returns_empty_slots() -> None:
    slots = extract_persona_slots("")
    assert slots.is_empty()


def test_build_persona_block_empty_returns_empty_string() -> None:
    assert build_persona_block(extract_persona_slots("")) == ""


def test_build_persona_block_contains_required_directive() -> None:
    slots = extract_persona_slots("cho mẹ bỉm 25-35 tuổi, lão hóa da")
    block = build_persona_block(slots)
    # Must surface the extracted age + cohort + pain
    assert "25-35" in block
    assert "mẹ bỉm sữa" in block
    assert "lão hóa" in block
    # Must include the required-address directive so the model can't drop it
    assert "BẮT BUỘC" in block
