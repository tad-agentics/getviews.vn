"""voice_copy — humanize stats jargon in narrative prose."""

from __future__ import annotations

from getviews_pipeline.voice_copy import (
    humanize_narrative_vi_dict,
    humanize_stats_prose,
    humanize_video_report_out,
)


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


def test_humanize_stats_prose_round2_jargon() -> None:
    raw = (
        "Format 'Faceless' thiếu pain point rõ. Dùng template hook + Tip "
        "để tăng discoverability. Lời promise phải có trong 3 giây đầu."
    )
    out = humanize_stats_prose(raw)
    lowered = out.lower()
    for banned in (
        "pain point",
        "format",
        "template",
        "tip",
        "faceless",
        "discoverability",
        "promise",
    ):
        assert banned not in lowered, f"{banned!r} leaked: {out!r}"
    assert "định dạng không lộ mặt" in lowered
    assert "điểm nhạy" in out


def test_humanize_stats_prose_round3_signal_jargon_and_enums() -> None:
    raw = (
        "Thiếu neo giá trị (price anchor) khiến hook curiosity_gap yếu. "
        "Persona thiếu negative markers trong transcript."
    )
    out = humanize_stats_prose(raw)
    lowered = out.lower()
    for banned in (
        "price anchor",
        "negative markers",
        "curiosity_gap",
        "transcript",
    ):
        assert banned not in lowered, f"{banned!r} leaked: {out!r}"
    assert "neo giá" in lowered
    assert "dấu hiệu tiêu cực" in lowered
    assert "tạo khoảng trống tò mò" in lowered
    assert "lời thoại" in lowered


def test_humanize_stats_prose_completion_rate_and_duplicate_jargon() -> None:
    raw = "Thiếu ngắt nhịp (pattern interrupt) — completion rate thấp."
    out = humanize_stats_prose(raw)
    assert "completion rate" not in out.lower()
    assert "pattern interrupt" not in out.lower()
    assert "tỷ lệ xem hết" in out.lower()
    assert "(ngắt nhịp)" not in out.lower()
    assert "ngắt nhịp" in out.lower()


def test_humanize_video_report_out_sanitizes_enrichment() -> None:
    out = {
        "narrative_vi": {"headline_vi": "Format faceless — pain point yếu"},
        "enrichment": {
            "pain_points": ["Main pain point: no promise in hook"],
            "target_audience": "Gym creators using tutorial template",
        },
        "errors": [{"title": "Weak promise", "detail": "No pain point", "fix": "Add Tip"}],
    }
    humanize_video_report_out(out)
    headline = out["narrative_vi"]["headline_vi"].lower()
    assert "format" not in headline
    assert "pain point" not in headline
    assert "promise" not in out["errors"][0]["title"].lower()
    assert "pain point" not in out["enrichment"]["pain_points"][0].lower()


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
