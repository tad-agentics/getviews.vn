"""Tests for channel_diagnose_prompts.py — context builder + prompt parser.

Golden-file context tests: one per trajectory shape (6 total).
Prompt parser tests: assert section-ID split + TITLE extraction works on
fixture LLM outputs for each trajectory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "channel_diagnose"


def _load_normalised(name: str) -> list[dict[str, Any]]:
    with open(FIXTURE_DIR / f"{name}.json") as f:
        awemes = json.load(f)
    from getviews_pipeline.channel_diagnose import _normalise_aweme
    return [v for aw in awemes if (v := _normalise_aweme(aw)) is not None]


def _build_context(
    trajectory: str,
    videos: list[dict[str, Any]] | None = None,
    next_video_concept: dict[str, Any] | None = None,
) -> str:
    from getviews_pipeline.channel_diagnose import (
        build_channel_pattern,
        compute_inflection_point,
        compute_recent_window_stats,
    )
    from getviews_pipeline.channel_diagnose_prompts import build_channel_diagnosis_context

    if videos is None:
        videos = _load_normalised(trajectory)

    pattern = build_channel_pattern(videos)
    recent = compute_recent_window_stats(videos)
    inflection = compute_inflection_point(videos)

    return build_channel_diagnosis_context(
        handle="testcreator",
        videos=videos,
        trajectory=trajectory,  # type: ignore[arg-type]
        channel_pattern=pattern,
        recent_window_30d=recent,
        inflection=inflection,
        top_performers=[],
        worst_performers=[],
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks=None,
        next_video_concept=next_video_concept,
    )


# ---------------------------------------------------------------------------
# Copy-rules compliance checks
# ---------------------------------------------------------------------------


def test_system_prompt_no_forbidden_phrases():
    """Verify the system prompt bans copy-rules.mdc forbidden phrases as examples,
    and does NOT use them in its own instructional sentences.
    The prompt is allowed to LIST them under 'KHÔNG dùng' — that's intentional."""
    from getviews_pipeline.channel_diagnose_prompts import CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # The prompt must instruct the LLM to avoid these phrases
    assert "KHÔNG dùng" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # The prompt must NOT greet with these phrases as part of writing instructions
    # (Checking that they only appear in the "KHÔNG dùng" list context)
    assert 'Chào bạn,"' not in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT  # actual greeting use
    assert "công thức vàng là" not in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT  # actual usage


def test_system_prompt_has_stable_section_ids():
    from getviews_pipeline.channel_diagnose_prompts import CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    required_ids = [
        "=== verdict ===",
        "=== what_worked ===",
        "=== what_falling ===",
        "=== video_vs_channel ===",
        "=== competitive_landscape ===",
        "=== recommendations ===",
    ]
    for sid in required_ids:
        assert sid in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT, f"Missing section ID: {sid}"


def test_system_prompt_lightreel_evidence_contract():
    """2026-06-11 Lightreel audit — pin the four structural instructions:
    pattern-lock threshold rule, causal verdict (no algorithm excuse),
    coined archetype labels, and the next_video anti-repeat clause."""
    from getviews_pipeline.channel_diagnose_prompts import CHANNEL_DIAGNOSIS_SYSTEM_PROMPT

    # §what_worked — induced threshold rule with the fabrication guard.
    assert "KHÓA PATTERN" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    assert "THẤP HƠN view của video thấp nhất" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # §verdict — causal attribution tied to the inflection format-mix shift.
    assert "đen đủi thuật toán" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    assert "KHÔNG đổ cho thuật toán khi format mix đã đổi" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # §what_worked / §what_falling — coined archetype labels, reused in §7.
    assert CHANNEL_DIAGNOSIS_SYSTEM_PROMPT.count("tên pattern 2-4 từ tự đặt") == 2
    assert "gọi lại đúng **tên pattern**" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # §next_video — anti-repeat differentiation clause.
    assert "KHÁC GÌ LẦN TRƯỚC" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT


def test_system_prompt_no_time_bucket_markers():
    from getviews_pipeline.channel_diagnose_prompts import CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # The prompt must explicitly ban pill tokens (they appear in the KHÔNG dùng rules)
    assert "[[cite:" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT  # mentioned as banned
    assert "[[creator:" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT  # mentioned as banned
    # Time-bucket markers are listed as examples of what NOT to use
    assert "KHÔNG dùng nhãn thời gian" in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT
    # The prompt must not produce these as instructional examples outside the rule block
    assert "[[cite:video_id]]" not in CHANNEL_DIAGNOSIS_SYSTEM_PROMPT  # full example use


# ---------------------------------------------------------------------------
# Context builder — <<<>>> vs === delimiter checks
# ---------------------------------------------------------------------------


def test_context_uses_angle_bracket_delimiters():
    ctx = _build_context("decline_from_peak")
    assert "<<<SCENARIO>>>" in ctx
    # Must NOT use === for input blocks (would collide with output regex)
    assert "=== SCENARIO" not in ctx


def test_context_has_scenario_block():
    ctx = _build_context("decline_from_peak")
    assert "trajectory: decline_from_peak" in ctx
    assert "total_videos:" in ctx
    assert "peak_views:" in ctx


def test_context_worst_performers_omitted_for_breakout():
    ctx = _build_context("breakout")
    assert "<<<WORST RECENT PERFORMERS>>>" not in ctx


def test_context_worst_performers_omitted_for_new_account():
    ctx = _build_context("new_account")
    assert "<<<WORST RECENT PERFORMERS>>>" not in ctx


def test_context_worst_performers_present_for_stagnant():
    videos = _load_normalised("stagnant")
    from getviews_pipeline.channel_diagnose import (
        build_channel_pattern,
        compute_inflection_point,
        compute_recent_window_stats,
        select_worst_performers,
    )
    from getviews_pipeline.channel_diagnose_prompts import build_channel_diagnosis_context

    pattern = build_channel_pattern(videos)
    recent = compute_recent_window_stats(videos)
    inflection = compute_inflection_point(videos)
    worst = select_worst_performers(videos)

    ctx = build_channel_diagnosis_context(
        handle="testcreator",
        videos=videos,
        trajectory="stagnant",
        channel_pattern=pattern,
        recent_window_30d=recent,
        inflection=inflection,
        top_performers=[],
        worst_performers=[t for t in worst],  # type: ignore[misc]
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks=None,
    )
    assert "<<<WORST RECENT PERFORMERS>>>" in ctx


def test_context_niche_benchmark_omitted_when_thin():
    ctx = _build_context("stagnant")
    # niche_benchmarks=None → omitted
    assert "<<<NICHE BENCHMARK>>>" not in ctx


def test_context_niche_benchmark_included_when_enough_peers():
    videos = _load_normalised("stagnant")
    from getviews_pipeline.channel_diagnose import (
        build_channel_pattern,
        compute_inflection_point,
        compute_recent_window_stats,
    )
    from getviews_pipeline.channel_diagnose_prompts import build_channel_diagnosis_context

    pattern = build_channel_pattern(videos)
    recent = compute_recent_window_stats(videos)
    inflection = compute_inflection_point(videos)

    ctx = build_channel_diagnosis_context(
        handle="testcreator",
        videos=videos,
        trajectory="stagnant",
        channel_pattern=pattern,
        recent_window_30d=recent,
        inflection=inflection,
        top_performers=[],
        worst_performers=[],
        creator_match=None,
        ugc_creators=[],
        niche_benchmarks={"channel_count": 15, "avg_views_p50": 20_000, "avg_views_p75": 50_000, "engagement_p75": 0.05},
    )
    assert "<<<NICHE BENCHMARK>>>" in ctx


def test_context_ugc_empty_placeholder():
    ctx = _build_context("stagnant")
    assert "<<<KÊNH CÙNG NGÁCH" in ctx
    assert "Không đủ kênh cùng ngách trong kho dữ liệu" in ctx


def _next_video_concept(peer_avg_views: int) -> dict[str, Any]:
    return {
        "format": "talking_head",
        "format_label": "Nói trước camera",
        "duration_sec": 18,
        "rationale_struct": "x",
        "sample_peer_handle": "peer",
        "sample_video_url": "https://www.tiktok.com/@peer/video/1",
        "peer_avg_views": peer_avg_views,
        "channel_share_pct": 3.0,
    }


def test_context_next_video_includes_peer_avg_when_real():
    ctx = _build_context("stagnant", next_video_concept=_next_video_concept(120_000))
    assert "<<<NEXT VIDEO CONCEPT>>>" in ctx
    assert "peer_avg_views:" in ctx


def test_context_next_video_omits_peer_avg_when_zero():
    """Bug 2026-06-12: peer_avg_views=0 reached the prompt and Gemini parroted
    «Peer TB ~0 view» in the GỢI Ý box."""
    ctx = _build_context("stagnant", next_video_concept=_next_video_concept(0))
    assert "<<<NEXT VIDEO CONCEPT>>>" in ctx
    assert "peer_avg_views" not in ctx


# ---------------------------------------------------------------------------
# Context builder — one assertion per trajectory shape
# ---------------------------------------------------------------------------


def test_context_decline_from_peak_has_trajectory():
    ctx = _build_context("decline_from_peak")
    assert "trajectory: decline_from_peak" in ctx


def test_context_stagnant_has_trajectory():
    ctx = _build_context("stagnant")
    assert "trajectory: stagnant" in ctx


def test_context_steady_growth_has_trajectory():
    ctx = _build_context("steady_growth")
    assert "trajectory: steady_growth" in ctx


def test_context_breakout_has_trajectory():
    ctx = _build_context("breakout")
    assert "trajectory: breakout" in ctx


def test_context_bursty_has_trajectory():
    ctx = _build_context("bursty")
    assert "trajectory: bursty" in ctx


def test_context_new_account_has_trajectory():
    ctx = _build_context("new_account")
    assert "trajectory: new_account" in ctx


# ---------------------------------------------------------------------------
# DEFAULT_TITLES
# ---------------------------------------------------------------------------


def test_default_titles_all_6_trajectories_all_sections():
    from getviews_pipeline.channel_diagnose_prompts import DEFAULT_TITLES
    trajectories = ["decline_from_peak", "stagnant", "steady_growth", "breakout", "bursty", "new_account"]
    sections = ["verdict", "what_worked", "competitive_landscape", "recommendations"]
    for t in trajectories:
        for s in sections:
            assert (s, t) in DEFAULT_TITLES, f"Missing DEFAULT_TITLES[({s!r}, {t!r})]"


def test_default_titles_what_falling_not_for_breakout_new_account():
    from getviews_pipeline.channel_diagnose_prompts import DEFAULT_TITLES
    # what_falling is only in DEFAULT_TITLES for trajectories that emit it
    assert ("what_falling", "breakout") not in DEFAULT_TITLES
    assert ("what_falling", "new_account") not in DEFAULT_TITLES
    # But it IS there for decline_from_peak
    assert ("what_falling", "decline_from_peak") in DEFAULT_TITLES


# ---------------------------------------------------------------------------
# Prompt parser tests — section-ID split + TITLE extraction
# ---------------------------------------------------------------------------

SECTION_HEADER_RE = re.compile(
    r"^=== (verdict|what_worked|what_falling|video_vs_channel|competitive_landscape|recommendations) ===$",
    re.MULTILINE,
)
TITLE_RE = re.compile(r"^TITLE:\s*(.+)$", re.MULTILINE)


def _make_fixture_narrative(trajectory: str) -> str:
    """Build a minimal fixture LLM narrative for the given trajectory."""
    what_falling = "" if trajectory in ("breakout", "new_account") else (
        "\n=== what_falling ===\n"
        "TITLE: NHỮNG GÌ ĐANG GIẢM\n"
        "Đây là nội dung section 3.\n"
    )
    return (
        f"=== verdict ===\n"
        f"TITLE: BỨC TRANH TỔNG THỂ\n"
        f"Đây là nội dung verdict cho {trajectory}.\n"
        f"\n"
        f"=== what_worked ===\n"
        f"TITLE: NHỮNG GÌ TỪNG HOẠT ĐỘNG\n"
        f"Section 2 nội dung.\n"
        f"{what_falling}"
        f"\n"
        f"=== competitive_landscape ===\n"
        f"TITLE: ĐỐI THỦ ĐANG LÀM GÌ\n"
        f"Section 5 nội dung.\n"
        f"\n"
        f"=== recommendations ===\n"
        f"TITLE: KẾ HOẠCH HÀNH ĐỘNG\n"
        f"1. **Làm điều này trước**\n"
        f"Vì dữ liệu cho thấy X.\n"
        f"\n"
        f"2. **Thứ hai cần làm**\n"
        f"Dữ liệu Y cho thấy điều này.\n"
    )


def _parse_sections(narrative: str) -> dict[str, str]:
    """Parse a fixture narrative into {section_id: body_with_title} dict."""
    parts = SECTION_HEADER_RE.split(narrative)
    result: dict[str, str] = {}
    # parts[0] = text before first header (usually empty)
    # then pairs of (section_id, body)
    for i in range(1, len(parts), 2):
        section_id = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        result[section_id] = body.strip()
    return result


def _extract_title(section_body: str) -> str | None:
    m = TITLE_RE.search(section_body)
    return m.group(1).strip() if m else None


def test_parser_split_decline_from_peak():
    narrative = _make_fixture_narrative("decline_from_peak")
    sections = _parse_sections(narrative)
    assert "verdict" in sections
    assert "what_worked" in sections
    assert "what_falling" in sections
    assert "competitive_landscape" in sections
    assert "recommendations" in sections


def test_parser_split_breakout_no_what_falling():
    narrative = _make_fixture_narrative("breakout")
    sections = _parse_sections(narrative)
    assert "verdict" in sections
    assert "what_falling" not in sections
    assert "recommendations" in sections


def test_parser_split_new_account_no_what_falling():
    narrative = _make_fixture_narrative("new_account")
    sections = _parse_sections(narrative)
    assert "what_falling" not in sections


def test_parser_title_extraction():
    narrative = _make_fixture_narrative("stagnant")
    sections = _parse_sections(narrative)
    title = _extract_title(sections["verdict"])
    assert title == "BỨC TRANH TỔNG THỂ"


def test_parser_recommendation_items():
    narrative = _make_fixture_narrative("stagnant")
    sections = _parse_sections(narrative)
    rec_body = sections.get("recommendations", "")
    # Should find at least 2 numbered items with bold leads
    rec_re = re.compile(r"^\s*(\d+)\.\s+\*\*(.+?)\*\*", re.MULTILINE)
    matches = rec_re.findall(rec_body)
    assert len(matches) >= 2, f"Expected ≥2 recommendations, found {len(matches)}"


def test_parser_handles_all_6_trajectories():
    for traj in ["decline_from_peak", "stagnant", "steady_growth", "breakout", "bursty", "new_account"]:
        narrative = _make_fixture_narrative(traj)
        sections = _parse_sections(narrative)
        assert "verdict" in sections, f"verdict missing for {traj}"
        assert "recommendations" in sections, f"recommendations missing for {traj}"
