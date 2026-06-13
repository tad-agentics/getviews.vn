"""Regression tests for the 2026-06-12 live video-diagnosis report audit.

Covers:
- headline_vi markdown stripping (literal ``**`` rendered on the report),
- seeding claim single-surface dedupe (findings card duplicated the boost block),
- Vietnamese enum labels in signal claims (raw ``curiosity_gap`` /
  ``entertainment_first`` leaked into prose),
- prompt rules backing all three.
"""

from __future__ import annotations

from getviews_pipeline.diagnose_prompts import DIAGNOSIS_V6_JSON_INSTRUCTION
from getviews_pipeline.gemini import (
    _dedupe_seeding_claim_surfaces,
    _normalize_narrative_vi_dict,
)
from getviews_pipeline.signals.commerce import extract_conversion_objective_signal
from getviews_pipeline.signals.hook import extract_hook_type_niche_mismatch_signal
from getviews_pipeline.signals.win import extract_win_hook_aligns_niche_top_signal

# ---------------------------------------------------------------------------
# Bug 2 — headline_vi markdown artifact
# ---------------------------------------------------------------------------


def test_normalize_strips_markdown_emphasis_from_headline() -> None:
    out = _normalize_narrative_vi_dict(
        {"headline_vi": "**Video thắng nhờ hook 0-3s** — giữ nhịp này."}
    )
    assert out is not None
    assert out["headline_vi"] == "Video thắng nhờ hook 0-3s — giữ nhịp này."
    assert "*" not in out["headline_vi"]


def test_normalize_strips_markdown_from_fallback_headline() -> None:
    out = _normalize_narrative_vi_dict(
        {"headline_vi": "", "ket_luan_nhanh": "*Kết luận* nhanh có `code`."}
    )
    assert out is not None
    assert "*" not in out["headline_vi"]
    assert "`" not in out["headline_vi"]


def test_normalize_headline_never_empty_after_strip() -> None:
    out = _normalize_narrative_vi_dict({"headline_vi": "**"})
    assert out is not None
    assert out["headline_vi"] == "—"


def test_prompt_forbids_markdown_in_headline() -> None:
    assert "KHÔNG dùng ** hay markdown trong headline_vi" in DIAGNOSIS_V6_JSON_INSTRUCTION


# ---------------------------------------------------------------------------
# Bug 3 — seeding claim feeds ONE surface (boost_attribution block)
# ---------------------------------------------------------------------------


def _diag(sections: list[dict]) -> dict:
    return {"headline_vi": "h", "sections": sections, "evidence_anchors": []}


def test_seeding_finding_dropped_when_boost_section_present() -> None:
    diag = _diag(
        [
            {
                "section_id": "diagnosis",
                "findings": [
                    {
                        "title_vi": "Comment có dấu hiệu seeding",
                        "body_vi": "93% comment trung tính.",
                        "fix_vi": "Kiểm tra comment thật.",
                    },
                    {
                        "title_vi": "Hook chậm — mất người xem",
                        "body_vi": "3 giây đầu là cảnh tĩnh.",
                        "fix_vi": "Mở bằng chuyển động.",
                    },
                ],
            },
            {
                "section_id": "boost_attribution",
                "text": "**Có dấu hiệu seeding ảo** — comment trung tính cao.",
                "findings": [
                    {"title_vi": "Seeding", "body_vi": "x", "fix_vi": "y"},
                ],
            },
        ]
    )
    _dedupe_seeding_claim_surfaces(diag)
    diagnosis_findings = diag["sections"][0]["findings"]
    assert len(diagnosis_findings) == 1
    assert diagnosis_findings[0]["title_vi"] == "Hook chậm — mất người xem"
    # boost_attribution is not issue-based — findings forced empty; the claim
    # lives in its text (the nguồn-lượt-xem block).
    assert diag["sections"][1]["findings"] == []
    assert "seeding" in diag["sections"][1]["text"].lower()


def test_seeding_finding_kept_when_no_boost_section() -> None:
    diag = _diag(
        [
            {
                "section_id": "diagnosis",
                "findings": [
                    {"title_vi": "Comment có dấu hiệu seeding", "body_vi": "x", "fix_vi": "y"},
                ],
            }
        ]
    )
    _dedupe_seeding_claim_surfaces(diag)
    assert len(diag["sections"][0]["findings"]) == 1


def test_prompt_declares_seeding_single_surface_rule() -> None:
    assert "chỉ được diễn đạt MỘT lần" in DIAGNOSIS_V6_JSON_INSTRUCTION


# ---------------------------------------------------------------------------
# Bug 4 — Vietnamese enum labels in claims + prompt rule
# ---------------------------------------------------------------------------


def test_hook_mismatch_claim_carries_vietnamese_label() -> None:
    ctx = {
        "user_analysis": {"hook_analysis": {"hook_type": "curiosity_gap"}},
        "niche_meta": {
            "sample_size": 100,
            "hook_distribution": {"question": 40, "how_to": 30, "story_open": 20},
        },
    }
    sigs = extract_hook_type_niche_mismatch_signal(ctx)
    assert len(sigs) == 1
    claim = sigs[0].claim
    assert "Tạo khoảng trống tò mò" in claim  # VN label leads
    assert "(curiosity_gap)" in claim  # enum kept in parens
    assert "Đặt câu hỏi" in claim  # top hooks labelled too


def test_win_hook_aligns_claim_carries_vietnamese_label() -> None:
    ctx = {
        "performance_tier": "hit",
        "user_analysis": {"hook_analysis": {"hook_type": "question"}},
        "niche_meta": {
            "sample_size": 100,
            "hook_distribution": {"question": 40, "how_to": 30, "story_open": 20},
        },
        "user_stats": {},
    }
    sigs = extract_win_hook_aligns_niche_top_signal(ctx)
    assert len(sigs) == 1
    assert "Đặt câu hỏi" in sigs[0].claim
    assert "(question)" in sigs[0].claim
    assert "`question`" not in sigs[0].claim


def test_conversion_objective_claim_carries_vietnamese_label() -> None:
    ctx = {
        "user_analysis": {
            "promotion_type": "organic",
            "commerce_intent": {"conversion_objective": "shop_direct"},
        },
    }
    sigs = extract_conversion_objective_signal(ctx)
    assert len(sigs) == 1
    claim = sigs[0].claim
    assert "Bán hàng TikTok Shop trực tiếp" in claim
    assert "(shop_direct)" in claim
    assert "đang là shop_direct" not in claim


def test_prompt_forbids_raw_enums_in_prose() -> None:
    assert "ENUM PHẢI DỊCH" in DIAGNOSIS_V6_JSON_INSTRUCTION
    assert "«curiosity_gap»" in DIAGNOSIS_V6_JSON_INSTRUCTION


# ---------------------------------------------------------------------------
# Retired next_video section — stripped from v6 video diagnosis pool (2026-06-13)
# ---------------------------------------------------------------------------


def test_drop_retired_v6_sections_removes_next_video() -> None:
    from getviews_pipeline.gemini import _drop_retired_v6_sections

    diag = {
        "headline_vi": "h",
        "sections": [
            {"section_id": "diagnosis", "text": "**Verdict.**"},
            {"section_id": "next_video", "text": "• Hook (0-1s): câu mở"},
        ],
    }
    _drop_retired_v6_sections(diag)
    assert [s["section_id"] for s in diag["sections"]] == ["diagnosis"]


def test_parse_v6_pool_response_strips_retired_next_video() -> None:
    import json

    from getviews_pipeline.gemini import _parse_diagnosis_v6_pool_response

    payload = {
        "diagnosis_vi": {
            "headline_vi": "Verdict.",
            "sections": [
                {"section_id": "diagnosis", "text": "**Verdict.** Ngắn."},
                {
                    "section_id": "next_video",
                    "title": "Video tiếp theo nên quay",
                    "text": "• Hook (0-1s): câu mở",
                    "findings": [],
                },
            ],
            "evidence_anchors": [],
        },
        "format_cards": [],
    }
    text = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
    _, narrative_vi, _, diag_vi = _parse_diagnosis_v6_pool_response(
        text, allowed=set(), reference_videos=[]
    )
    assert diag_vi is not None
    assert [s["section_id"] for s in diag_vi["sections"]] == ["diagnosis"]
    assert narrative_vi is not None


def test_v6_prompt_no_longer_mentions_next_video_section() -> None:
    assert "NEXT_VIDEO" not in DIAGNOSIS_V6_JSON_INSTRUCTION
    assert "next_video là object" not in DIAGNOSIS_V6_JSON_INSTRUCTION
