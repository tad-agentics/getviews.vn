"""Regression tests for ``classify_format`` — taxonomy lock enforcement.

The Vietnamese patterns below were added 2026-05-09 (state-of-corpus
Axis 2 step) to pull real rows out of the 'other' catch-all. Each
test pins a specific live corpus example that used to bucket to
'other' but now routes to its correct bucket.

Priority-order regressions also pinned so a future regex tweak can't
silently flip a correct classification.
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.corpus_ingest import classify_format


def _analysis(transcript: str = "", *, topics: list[str] | None = None,
              scenes: list[dict[str, Any]] | None = None,
              tone: str = "") -> dict[str, Any]:
    return {
        "audio_transcript": transcript,
        "topics": topics or [],
        "scenes": scenes or [],
        "tone": tone,
    }


# ── storytelling — VN narrative markers ──────────────────────────────


def test_narrative_nang_dau_routes_to_storytelling() -> None:
    """Real corpus row: Philippines daughter-in-law cultural story."""
    analysis = _analysis(
        "Nàng dâu người Philippines 42 tuổi, lấy chồng sang Hàn Quốc "
        "đã 16 năm nhưng chưa một lần về thăm nhà đẻ",
        topics=["Culture", "Family"],
    )
    assert classify_format(analysis, niche_id=16) == "storytelling"


def test_cau_chuyen_routes_to_storytelling() -> None:
    analysis = _analysis("Hôm nay mình kể về câu chuyện của một người bạn")
    assert classify_format(analysis, niche_id=13) == "storytelling"


def test_dang_sau_la_routes_to_storytelling() -> None:
    """Reveal-framed narratives ('the reason behind is…')."""
    analysis = _analysis("Lý do đằng sau là gì? Mời các bạn cùng khám phá")
    assert classify_format(analysis, niche_id=13) == "storytelling"


# ── tutorial — VN procedural markers ─────────────────────────────────


def test_quyet_toan_routes_to_tutorial() -> None:
    """Real corpus row: tax filing explainer."""
    analysis = _analysis(
        "Khẩn: Kiểm tra quyết toán thuế ngay, bạn có thể được hoàn trả "
        "cả chục triệu đồng.",
        topics=["Quyết toán thuế", "Hoàn thuế"],
    )
    assert classify_format(analysis, niche_id=15) == "tutorial"


def test_bi_quyet_routes_to_tutorial() -> None:
    analysis = _analysis("Chia sẻ bí quyết giúp bạn làm việc hiệu quả hơn")
    assert classify_format(analysis, niche_id=7) == "tutorial"


def test_dang_ky_thu_tuc_routes_to_tutorial() -> None:
    analysis = _analysis("Cần chuẩn bị các thủ tục đăng ký như thế nào")
    assert classify_format(analysis, niche_id=12) == "tutorial"


# ── review — VN superiority / performance commentary ─────────────────


def test_an_dut_routes_to_review() -> None:
    """Real corpus row: music competition commentary."""
    analysis = _analysis(
        "Bài hát mà đối thủ trình diễn... Sơ sơ thôi cũng đã ăn đứt đối thủ",
        topics=["Music Competition", "Performance Comparison"],
    )
    assert classify_format(analysis, niche_id=6) == "review"


def test_phan_trinh_dien_routes_to_review() -> None:
    analysis = _analysis("Phần trình diễn của đối thủ có hồn quá")
    assert classify_format(analysis, niche_id=6) == "review"


# ── comparison — additional Vietnamese markers ───────────────────────


def test_khac_nhau_routes_to_comparison() -> None:
    analysis = _analysis("Có mấy điểm khác nhau giữa hai loại này")
    assert classify_format(analysis, niche_id=2) == "comparison"


# ── vlog — additional VN daily markers ───────────────────────────────


def test_hom_nay_minh_routes_to_vlog() -> None:
    analysis = _analysis("Hôm nay mình đi ra quán cafe quen thuộc")
    assert classify_format(analysis, niche_id=11) == "vlog"


# ── priority-order regressions ───────────────────────────────────────


def test_recipe_wins_over_new_tutorial_markers() -> None:
    """Recipes mentioning bí quyết (tutorial marker) should stay recipe."""
    analysis = _analysis("Công thức bí quyết nấu phở chuẩn vị bắc")
    assert classify_format(analysis, niche_id=4) == "recipe"


def test_review_still_wins_over_new_comparison_markers() -> None:
    """'đánh giá' + 'khác biệt' → review should win."""
    analysis = _analysis("Đánh giá sản phẩm, điểm khác biệt với đối thủ là")
    assert classify_format(analysis, niche_id=3) == "review"


def test_existing_patterns_still_route_correctly() -> None:
    """Smoke regressions for the original patterns."""
    assert classify_format(_analysis("ASMR mukbang cháo lòng"), 4) == "mukbang"
    assert classify_format(_analysis("GRWM morning routine"), 2) == "grwm"
    assert classify_format(_analysis("Mở hộp Shopee haul"), 3) == "haul"
    assert classify_format(
        _analysis("vs so sánh hai loại kem chống nắng"), 2,
    ) == "comparison"


def test_falls_through_to_other_for_no_markers() -> None:
    """News clips with no regex markers should still fall through."""
    analysis = _analysis(
        "Hôm qua công an phường Bắc Cam Ranh cho biết",
        topics=["An ninh trật tự", "ATM"],
    )
    assert classify_format(analysis, niche_id=13) == "other"
