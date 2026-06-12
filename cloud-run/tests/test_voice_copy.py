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


def test_humanize_stats_prose_strips_english_jargon() -> None:
    raw = (
        "Hook dùng pattern interrupt và text overlay. Persona là expert kiểu "
        "tutorial, archetype entertainment_first. Thêm overlay checklist để "
        "tăng bookmark. Có dead air và jump-cut. Đối chiếu corpus + heatmap."
    )
    out = humanize_stats_prose(raw)
    lowered = out.lower()
    for banned in (
        "pattern interrupt",
        "text overlay",
        "expert",
        "tutorial",
        "archetype",
        "entertainment_first",
        "overlay checklist",
        "bookmark",
        "dead air",
        "jump-cut",
        "corpus",
        "heatmap",
    ):
        assert banned not in lowered, f"{banned!r} leaked: {out!r}"
    assert "ngắt nhịp" in out
    assert "chữ trên màn hình" in out
    assert "chuyên gia" in out
    assert "hình mẫu" in out
    assert "danh sách bước trên màn hình" in out


def test_humanize_stats_prose_jargon_substrings_safe() -> None:
    # Vietnamese words must not be mangled by the whole-word jargon subs.
    raw = "Chuyên gia lưu ý: video này hướng dẫn rõ ràng."
    assert humanize_stats_prose(raw) == raw


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
