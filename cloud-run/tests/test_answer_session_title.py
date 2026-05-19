"""Option A — promote answer_sessions.title from narrative_vi.headline_vi."""

from __future__ import annotations

from getviews_pipeline.answer_session import (
    auto_title_from_initial_q,
    maybe_promote_session_title_from_video_narrative,
    title_from_headline_vi,
)


def test_auto_title_truncates_long_initial_q() -> None:
    q = "https://www.tiktok.com/@creator/video/" + ("1" * 100)
    title = auto_title_from_initial_q(q)
    assert title.endswith("…")
    assert len(title) == 81  # 80 chars + ellipsis


def test_auto_title_empty_initial_q() -> None:
    assert auto_title_from_initial_q("") == "Phiên nghiên cứu"
    assert auto_title_from_initial_q("   ") == "Phiên nghiên cứu"


def test_title_from_headline_vi_skips_placeholder() -> None:
    assert title_from_headline_vi("—") is None
    assert title_from_headline_vi("  ") is None


def test_promote_when_title_still_auto() -> None:
    initial_q = "https://vt.tiktok.com/ZSabc/"
    session = {
        "initial_q": initial_q,
        "title": auto_title_from_initial_q(initial_q),
    }
    report = {"narrative_vi": {"headline_vi": "Hook mở chậm khiến retention tụt ở 2s"}}
    assert (
        maybe_promote_session_title_from_video_narrative(session, report)
        == "Hook mở chậm khiến retention tụt ở 2s"
    )


def test_promote_skips_manual_rename() -> None:
    initial_q = "https://vt.tiktok.com/ZSabc/"
    session = {
        "initial_q": initial_q,
        "title": "Phân tích tuần này",
    }
    report = {"narrative_vi": {"headline_vi": "Headline mới"}}
    assert maybe_promote_session_title_from_video_narrative(session, report) is None


def test_promote_skips_when_headline_missing() -> None:
    initial_q = "short q"
    session = {"initial_q": initial_q, "title": auto_title_from_initial_q(initial_q)}
    assert maybe_promote_session_title_from_video_narrative(session, {}) is None
    assert (
        maybe_promote_session_title_from_video_narrative(
            session, {"narrative_vi": {"headline_vi": ""}}
        )
        is None
    )
