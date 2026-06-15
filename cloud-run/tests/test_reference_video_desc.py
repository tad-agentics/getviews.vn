"""Reference pool desc must not leak internal transcript guard markers."""

from __future__ import annotations

from getviews_pipeline.analysis_guards import TRANSCRIPT_UNAVAILABLE_MARKER
from getviews_pipeline.corpus_context import _reference_video_desc


def test_reference_video_desc_prefers_tiktok_caption_over_failed_transcript() -> None:
    row = {
        "caption": "Get ready with meee. Hôm nay hãy cùng mình makeup nhẹ",
    }
    analysis = {"audio_transcript": TRANSCRIPT_UNAVAILABLE_MARKER}
    desc = _reference_video_desc(row, analysis)
    assert desc.startswith("Get ready with meee")
    assert "Transcript không khả dụng" not in desc


def test_reference_video_desc_strips_marker_when_caption_missing() -> None:
    row: dict = {}
    analysis = {
        "audio_transcript": TRANSCRIPT_UNAVAILABLE_MARKER,
        "topics": ["makeup", "skincare"],
        "content_context": {"subject_matter": "Hướng dẫn trang điểm nhẹ nhàng"},
    }
    desc = _reference_video_desc(row, analysis)
    assert "Transcript không khả dụng" not in desc
    assert "makeup" in desc
    assert "trang điểm" in desc


def test_reference_video_desc_uses_usable_transcript_when_no_caption() -> None:
    row: dict = {}
    analysis = {
        "audio_transcript": "Hôm nay mình sẽ review kem chống nắng cho da dầu nhé các bạn",
    }
    desc = _reference_video_desc(row, analysis)
    assert desc.startswith("Hôm nay mình sẽ review")
