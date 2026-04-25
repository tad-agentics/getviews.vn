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


# ── has_speech gate — pins the recipe/tutorial silent-transcript fix ──


def test_silent_transcript_with_cooking_topic_is_not_recipe() -> None:
    """Regression for the eval harness miss: cat video with
    'nấu ăn' topic + [Không có lời thoại] transcript was mis-tagged
    recipe. Verbal-first formats now require actual speech."""
    analysis = _analysis(
        "[Không có lời thoại, chỉ có nhạc nền bài hát Until I Found You]",
        topics=["mèo", "nấu ăn", "thú cưng", "tình cảm"],
    )
    assert classify_format(analysis, niche_id=19) == "other"


def test_silent_transcript_with_tutorial_topic_is_not_tutorial() -> None:
    """Same rule applies to tutorial — a music-only clip with a
    'hướng dẫn' topic shouldn't become a tutorial."""
    analysis = _analysis(
        "[âm nhạc]",
        topics=["hướng dẫn trang điểm"],
    )
    assert classify_format(analysis, niche_id=2) == "other"


def test_recipe_still_matches_when_transcript_has_cooking_words() -> None:
    """Guard against over-correcting: real recipe videos with speech
    still route to recipe."""
    analysis = _analysis(
        "công thức làm bánh mì, 100 gram bột mì, bước 1 là",
        topics=["bánh mì"],
    )
    assert classify_format(analysis, niche_id=4) == "recipe"


# ── vlog — pins personal-business-journey pattern ────────────────────


def test_post_graduation_business_narrative_routes_to_vlog() -> None:
    """Regression for eval miss: 'sau khi tốt nghiệp, tôi lấy 3,5 tấn
    cam ra chợ phiên dựng sạp' — first-person life journey = vlog."""
    analysis = _analysis(
        "sau khi tốt nghiệp, tôi lấy 3,5 tấn cam, ra chợ phiên dựng sạp",
        topics=["Entrepreneurship", "Street Food Business"],
    )
    assert classify_format(analysis, niche_id=12) == "vlog"


# ── storytelling — pins drama/skit + southern dialect ───────────────


def test_drama_skit_topic_routes_to_comedy_skit_post_taxonomy_expansion() -> None:
    """Post-Wave-5+ taxonomy expansion: 'skit'-topic rows in niche 13
    now claim ``comedy_skit`` (scripted dialogue comedy) rather than
    ``storytelling`` (narrative recall). The 'skit' token is a
    stronger signal for dialogue comedy than the ``hoàn cảnh`` token
    is for narrative recall, so the priority order reflects that.

    This test was previously pinned to ``storytelling`` as a
    pre-taxonomy-expansion compromise; the update is the intended
    semantic improvement."""
    analysis = _analysis(
        "tui đứng thất vọng với bà luôn á, cái hoàn cảnh nhà thằng Nhật",
        topics=["drama", "skit", "school life"],
    )
    assert classify_format(analysis, niche_id=13) == "comedy_skit"


def test_hoan_canh_routes_to_storytelling() -> None:
    """'hoàn cảnh' is a VN life-story marker."""
    analysis = _analysis("Hoàn cảnh gia đình khó khăn mỗi ngày khắc nghiệt")
    assert classify_format(analysis, niche_id=16) == "storytelling"


# ── Wave 5+ word-boundary regression — `history` must not fire `story` ──
#
# Pre-fix the storytelling regex used a bare ``story`` substring inside
# an alternation, so any text containing ``history`` (or other ``story``-
# substrings like ``hashstory``, ``directory``…) false-fired the
# storytelling bucket. The fix wraps bare-token English loanwords
# (``story`` / ``drama`` / ``skit``) with ``\b`` word boundaries; multi-
# word VN phrases already have implicit boundaries via the space.

def test_history_keyword_does_not_fire_storytelling() -> None:
    """Regression for the eval-harness ``history → story`` substring
    miss. ``History class with my teacher`` is education content, NOT
    a narrative skit."""
    analysis = _analysis(
        "history class with my teacher today was wild",
        topics=["education", "history"],
    )
    # Without the \b fix this fell into 'storytelling'; now it must
    # NOT match that branch (the test asserts the negative — what
    # bucket it lands in instead is up to downstream branches).
    assert classify_format(analysis, niche_id=8) != "storytelling"


def test_history_in_topic_does_not_fire_storytelling() -> None:
    """Same regression but with ``history`` in the topics list rather
    than the transcript — the regex matches against the joined
    transcript+topics blob so both code paths need the fix."""
    analysis = _analysis(
        "Today we cover World War II events",
        topics=["history", "war", "education"],
    )
    assert classify_format(analysis, niche_id=8) != "storytelling"


def test_story_word_alone_still_fires_storytelling() -> None:
    """The fix must not over-correct — a real ``story`` reference
    still routes to storytelling. Word-boundary preserves the legit
    case."""
    analysis = _analysis("Let me tell you a story about my grandmother")
    assert classify_format(analysis, niche_id=8) == "storytelling"


def test_dramatic_does_not_fire_storytelling() -> None:
    """Defensive — ``dramatic`` / ``dramatically`` shouldn't substring-
    match the bare ``drama`` token after the \\b fix."""
    analysis = _analysis(
        "the dramatic shift in product quality was unexpected",
        topics=["product review"],
    )
    assert classify_format(analysis, niche_id=8) != "storytelling"


def test_drama_word_alone_still_fires_storytelling() -> None:
    """Real ``drama`` topic still routes (matches the existing
    Southern-dialect drama-skit regression test above; this is the
    minimal-input form)."""
    analysis = _analysis("kể về drama nhà chồng", topics=["drama"])
    assert classify_format(analysis, niche_id=13) == "storytelling"
