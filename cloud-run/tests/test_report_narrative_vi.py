"""W5-2 — narrative_vi.headline_vi attachment on validate."""

from __future__ import annotations

from getviews_pipeline.report_types import _attach_narrative_vi_headline


def test_attach_narrative_vi_from_pattern_thesis() -> None:
    report = {"tldr": {"thesis": "Kết luận nhanh: Hook cảnh báo đang thắng"}}
    _attach_narrative_vi_headline(report, "pattern")
    assert report["narrative_vi"]["headline_vi"].startswith("Kết luận nhanh")


def test_attach_narrative_vi_from_generic_paragraph() -> None:
    report = {"narrative": {"paragraphs": ["Xu hướng tuần này tập trung vào hook cảnh báo."]}}
    _attach_narrative_vi_headline(report, "generic")
    assert report["narrative_vi"]["headline_vi"].startswith("Xu hướng")
