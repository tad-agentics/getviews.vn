"""video_report_coherence — mode/tier alignment and error filtering."""

from getviews_pipeline.video_report_coherence import (
    build_video_related_questions,
    filter_structural_errors_for_tier,
    infer_early_performance_tier,
    pipeline_reconcile_mode,
    reconcile_video_mode,
    tier_implies_win_framing,
)


def test_reconcile_flop_to_win_when_hit() -> None:
    assert reconcile_video_mode("flop", "hit") == "win"


def test_reconcile_flop_to_win_on_channel_breakout_average() -> None:
    assert (
        reconcile_video_mode(
            "flop",
            "average",
            views=406_098,
            creator_median_views=934,
            target_vs_creator_median=435.0,
        )
        == "win"
    )


def test_tier_implies_win_framing_channel_ratio() -> None:
    assert tier_implies_win_framing(
        "average",
        views=200_000,
        target_vs_creator_median=2.5,
    )


def test_infer_early_tier_channel_breakout() -> None:
    tier = infer_early_performance_tier(
        406_098,
        50_000.0,
        creator_median_views=934,
    )
    assert tier == "hit"


def test_pipeline_reconcile_mode() -> None:
    video = {"video_id": "v1", "views": 406_098, "creator_median_views": 934}
    niche = {"avg_views": 50_000}
    assert pipeline_reconcile_mode("flop", video, niche) == "win"


def test_reconcile_keeps_flop_when_tier_flop() -> None:
    assert reconcile_video_mode("flop", "flop") == "flop"


def test_filter_drops_retention_drop_on_hit() -> None:
    errors = [
        {
            "error_id": "ERR_retention_drop_3s",
            "sev": "high",
            "title": "Tỷ lệ giữ chân thấp",
            "detail": "Video mất 100% người xem tiềm năng ngay tại 3 giây đầu",
            "fix": "Chèn cận sản phẩm",
        },
        {
            "error_id": "ERR_hook_mismatch",
            "sev": "high",
            "title": "Hook lạc đề",
            "detail": "Hook nhắc đồng hồ trong ngách skincare",
            "fix": "Mở bằng sản phẩm skincare",
        },
    ]
    out = filter_structural_errors_for_tier(errors, "hit", views=406_098)
    assert len(out) == 1
    assert out[0]["error_id"] == "ERR_hook_mismatch"


def test_filter_drops_retention_on_channel_breakout_average() -> None:
    errors = [
        {
            "error_id": "ERR_retention_drop_3s",
            "sev": "high",
            "title": "Tỷ lệ giữ chân thấp",
            "detail": "Video mất 100% người xem",
            "fix": "x",
        },
    ]
    out = filter_structural_errors_for_tier(
        errors,
        "average",
        views=406_098,
        target_vs_creator_median=435.0,
    )
    assert out == []


def test_related_questions_hit_tier() -> None:
    qs = build_video_related_questions(
        performance_tier="hit",
        mode="win",
        creator_handle="embeireview",
        niche_label="Review đồng hồ",
        content_format="product_showcase",
    )
    assert len(qs) == 3
    assert all(len(q) <= 120 for q in qs)
