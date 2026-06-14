"""Tests for diagnosis hook leaderboard + comment grounding blocks."""

from __future__ import annotations

from getviews_pipeline.diagnose_prompts import build_diagnosis_v6_user_prompt
from getviews_pipeline.diagnosis_grounding import (
    COMMENT_MIN_SAMPLE,
    build_comment_signal_block,
    build_hook_leaderboard_block,
    compute_diagnosis_grounding,
)
from getviews_pipeline.enum_labels_vi import trend_vi


def _hook_rows_above_floor() -> list[dict]:
    return [
        {
            "hook_type": "question",
            "avg_views": 80_000,
            "sample_size": 28,
            "trend_direction": "rising",
        },
        {
            "hook_type": "bold_claim",
            "avg_views": 160_000,
            "sample_size": 30,
            "trend_direction": "stable",
        },
    ]


def test_hook_leaderboard_renders_rank_and_multiplier() -> None:
    block, tel = build_hook_leaderboard_block(
        _hook_rows_above_floor(),
        user_hook_type="question",
        class_label="Skincare review",
    )
    assert "HOOK_LEADERBOARD" in block
    assert "hạng 2/2" in block
    assert "2×" in block or "2.0×" in block
    assert tel["hook_leaderboard_emitted"] is True
    assert tel["hook_buckets_above_floor"] == 2


def test_hook_leaderboard_omits_when_total_below_floor() -> None:
    block, tel = build_hook_leaderboard_block(
        [{"hook_type": "question", "avg_views": 1000, "sample_size": 20}],
        user_hook_type="question",
        class_label="Ngách mỏng",
    )
    assert block == ""
    assert tel["hook_leaderboard_emitted"] is False


def test_hook_leaderboard_top_only_when_user_bucket_thin() -> None:
    rows = _hook_rows_above_floor() + [
        {"hook_type": "how_to", "avg_views": 500, "sample_size": 2, "trend_direction": "stable"},
    ]
    block, _ = build_hook_leaderboard_block(
        rows,
        user_hook_type="how_to",
        class_label="Skincare",
    )
    assert "Hook mạnh nhất ngách" in block
    assert "Hook bạn đang dùng" not in block


def test_comment_signal_happy_path() -> None:
    radar = {
        "sampled": 12,
        "language": "vi",
        "sentiment": {"positive_pct": 55.0, "negative_pct": 15.0, "neutral_pct": 30.0},
        "purchase_intent": {"count": 4, "top_phrases": ["mua ở đâu", "ship không"]},
        "questions_asked": 6,
    }
    block, tel = build_comment_signal_block(radar)
    assert "COMMENT_SIGNAL" in block
    assert "55%" in block
    assert "Câu hỏi lặp lại: 6" in block
    assert "mua ở đau" not in block  # typo guard
    assert "mua ở đâu" in block
    assert tel["comment_block_emitted"] is True
    assert tel["comment_sampled"] == 12


def test_comment_signal_below_sample_floor() -> None:
    block, tel = build_comment_signal_block(
        {"sampled": COMMENT_MIN_SAMPLE - 1, "language": "vi", "sentiment": {}},
    )
    assert block == ""
    assert tel["comment_block_emitted"] is False


def test_comment_signal_non_vi_language() -> None:
    block, _ = build_comment_signal_block(
        {"sampled": 20, "language": "en", "sentiment": {"positive_pct": 50, "negative_pct": 10}},
    )
    assert block == ""


def test_compute_diagnosis_grounding_respects_emit_flags() -> None:
    hook, comment, tel = compute_diagnosis_grounding(
        hook_effectiveness=_hook_rows_above_floor(),
        user_analysis={"hook_analysis": {"hook_type": "question"}},
        comment_radar={
            "sampled": 10,
            "language": "vi",
            "sentiment": {"positive_pct": 40, "negative_pct": 20},
            "questions_asked": 2,
        },
        class_label="Ngách",
        emit_hook=False,
        emit_comment=False,
    )
    assert hook == ""
    assert comment == ""
    assert tel["hook_block_would_emit"] is True
    assert tel["comment_block_would_emit"] is True


def test_trend_vi_maps_known_values() -> None:
    assert trend_vi("rising") == "đang tăng"
    assert trend_vi("stable") == "ổn định"
    assert trend_vi("declining") == "đang giảm"


def test_build_diagnosis_ctx_includes_hook_effectiveness() -> None:
    from getviews_pipeline.signals.registry import build_diagnosis_ctx

    rows = [{"hook_type": "question", "avg_views": 1, "sample_size": 1}]
    ctx = build_diagnosis_ctx(
        user_analysis={},
        user_stats={},
        reference_videos=[],
        channel_context=None,
        performance_tier="average",
        hook_effectiveness=rows,
    )
    assert ctx["hook_effectiveness"] == rows


def test_v6_prompt_includes_grounding_blocks_when_passed() -> None:
    hook_block = "HOOK_LEADERBOARD (ngách: Test, n_class=58):\n- Hook mạnh nhất ngách: X"
    comment_block = "COMMENT_SIGNAL (mẫu 10 bình luận):\n- Cảm xúc: tích cực 50%"
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis", "hook_analysis"],
        manifest_for_llm={},
        ctx={},
        content_format="review",
        niche_name="Test",
        corpus_size=100,
        reference_videos=[],
        user_analysis={"hook_analysis": {"hook_type": "question"}},
        user_stats={"views": 1000, "caption": "cap"},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
        hook_leaderboard_block=hook_block,
        comment_signal_block=comment_block,
    )
    assert "HOOK_LEADERBOARD" in prompt
    assert "COMMENT_SIGNAL" in prompt
    assert "HOOK_LEADERBOARD:" in prompt or "HOOK_LEADERBOARD (" in prompt


def test_v6_prompt_omits_grounding_when_blocks_empty() -> None:
    prompt = build_diagnosis_v6_user_prompt(
        sections_to_emit=["diagnosis"],
        manifest_for_llm={},
        ctx={},
        content_format="review",
        niche_name="Test",
        corpus_size=100,
        reference_videos=[],
        user_analysis={},
        user_stats={"views": 1000},
        performance_tier="average",
        channel_context=None,
        errors=None,
        wants_directions=False,
    )
    assert "HOOK_LEADERBOARD" not in prompt
    assert "COMMENT_SIGNAL" not in prompt
