"""voice_copy — humanize stats jargon in narrative prose."""

from __future__ import annotations

from getviews_pipeline.voice_copy import humanize_narrative_vi_dict, humanize_stats_prose


def test_humanize_stats_prose_median_and_p75() -> None:
    raw = (
        "gấp hơn 688 lần so với median 5.028 view của kênh. "
        "vượt ngưỡng 1,6% của p75 trong ngách thời trang nam."
    )
    out = humanize_stats_prose(raw)
    assert "mức view thường trên kênh" in out
    assert "median" not in out.lower()
    assert "trung vị" not in out.lower()
    assert "mức cao trong ngách (top 25%)" in out
    assert "p75" not in out.lower()


def test_humanize_narrative_vi_dict_walks_nested_sections() -> None:
    payload = {
        "headline_vi": "Hit",
        "diagnosis_vi": {
            "sections": [
                {"text_vi": "So với median kênh và p75 ngách."},
            ],
        },
    }
    out = humanize_narrative_vi_dict(payload)
    assert out is not None
    section_text = out["diagnosis_vi"]["sections"][0]["text_vi"]
    assert "mức view thường trên kênh" in section_text
    assert "mức cao trong ngách (top 25%)" in section_text
