"""video_report_coherence — mode/tier alignment and error filtering."""

from getviews_pipeline.video_report_coherence import (
    build_video_related_questions,
    effective_depth_tier,
    filter_structural_errors_for_tier,
    infer_early_performance_tier,
    max_findings_for_tier,
    pipeline_reconcile_mode,
    reconcile_video_mode,
    ref_n_for_tier,
    resolve_extraction_mode,
    resolve_stored_video_mode,
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


def test_resolve_stored_mode_from_tier() -> None:
    assert resolve_stored_video_mode("hit") == "win"
    assert resolve_stored_video_mode("flop") == "flop"
    assert resolve_stored_video_mode("early") == "win"
    assert resolve_stored_video_mode("average") == "win"


def test_caller_flop_overridden_when_tier_hit() -> None:
    assert reconcile_video_mode("flop", "hit", caller_mode="flop") == "win"


def test_unknown_tier_uses_query_hint() -> None:
    assert reconcile_video_mode("win", "unknown", query_hint="flop") == "flop"


def test_resolve_extraction_mode_early_never_flop() -> None:
    video = {"views": 500, "creator_median_views": 1000}
    assert resolve_extraction_mode("win", video, None, performance_tier="early") == "average"


def test_tier_depth_flop_more_than_hit() -> None:
    assert ref_n_for_tier("flop") > ref_n_for_tier("hit")
    assert max_findings_for_tier("flop") > max_findings_for_tier("hit")


def test_depth_levers_flop_strictly_exceeds_hit() -> None:
    """p2 acceptance — flop pulls strictly more refs AND more gap findings
    than a hit of the same niche, across every depth lever."""
    assert ref_n_for_tier("flop") > ref_n_for_tier("hit")
    assert max_findings_for_tier("flop") > max_findings_for_tier("hit")
    errs = [
        {"sev": "high", "error_id": f"ERR_{i}", "detail": "x"} for i in range(8)
    ]
    flop_kept = filter_structural_errors_for_tier(errs, "flop")
    hit_kept = filter_structural_errors_for_tier(errs, "hit", views=10)
    assert len(flop_kept) > len(hit_kept)


def test_effective_depth_tier_cohortless_flop_gets_flop_depth() -> None:
    # tier=unknown + resolved flop intent → full flop depth (the plan's
    # cohort-less flop guard).
    assert effective_depth_tier("unknown", "flop") == "flop"
    assert max_findings_for_tier(effective_depth_tier("unknown", "flop")) == (
        max_findings_for_tier("flop")
    )
    assert ref_n_for_tier(effective_depth_tier("unknown", "flop")) == (
        ref_n_for_tier("flop")
    )


def test_effective_depth_tier_passthrough_when_measured() -> None:
    # A measured tier is never overridden by intent.
    assert effective_depth_tier("hit", "flop") == "hit"
    assert effective_depth_tier("average", "flop") == "average"
    assert effective_depth_tier("unknown", "win") == "unknown"
    assert effective_depth_tier("unknown", None) == "unknown"


def test_resolve_extraction_mode_unknown_no_hint_is_average() -> None:
    # No cohort, no flop intent → neutral balanced prompt (never forced flop).
    assert resolve_extraction_mode("win", {"views": 500}, None) == "average"
    assert resolve_extraction_mode("win", {"views": 500}, {"avg_views": 0}) == "average"


def test_resolve_extraction_mode_unknown_flop_intent_is_flop() -> None:
    # Cohort-less flop guard at the extraction prompt level.
    assert resolve_extraction_mode("flop", {"views": 500}, None) == "flop"


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
