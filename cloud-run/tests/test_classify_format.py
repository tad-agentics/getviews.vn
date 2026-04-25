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


# ── Wave 5+ taxonomy expansion — gameplay ────────────────────────────
#
# Pins the new ``gameplay`` bucket (position 3 in classify_format) added
# 2026-04-25 per artifacts/docs/taxonomy-expansion.md §6.1. The bucket
# fires on niche=17 (Gaming & Esports) OR an explicit gaming topic in
# any niche.

def test_niche_17_fires_gameplay_unconditionally() -> None:
    """Niche 17 = Gaming & Esports. Any analysis routes to gameplay."""
    analysis = _analysis(
        "highlight match liên quân tối qua",
        topics=["mobile gaming"],
    )
    assert classify_format(analysis, niche_id=17) == "gameplay"


def test_gaming_topic_fires_gameplay_in_other_niches() -> None:
    """Gaming content in non-17 niches (e.g. tech-review niche) still
    routes to gameplay via the topic regex."""
    analysis = _analysis(
        "review điện thoại chơi game", topics=["gaming", "smartphone"],
    )
    assert classify_format(analysis, niche_id=9) == "gameplay"


def test_lien_quan_routes_to_gameplay() -> None:
    """Vietnamese MOBA — top-titles in the gameplay regex."""
    analysis = _analysis(
        "Pha xử lý đỉnh cao trong trận liên quân",
        topics=["liên quân"],
    )
    assert classify_format(analysis, niche_id=17) == "gameplay"


def test_roblox_topic_routes_to_gameplay() -> None:
    analysis = _analysis("Roblox map mới ra siêu vui", topics=["roblox"])
    assert classify_format(analysis, niche_id=17) == "gameplay"


def test_gameplay_wins_over_review_in_niche_17() -> None:
    """Niche 17 priority: even if 'review' appears in the transcript
    (e.g. a hero-review video), gameplay still wins because niche=17
    is the structural signal."""
    analysis = _analysis(
        "review tướng mới đánh giá chi tiết",
        topics=["liên quân", "hero review"],
    )
    assert classify_format(analysis, niche_id=17) == "gameplay"


def test_gameplay_wins_over_tutorial_when_gaming_topic_present() -> None:
    """Gaming-tutorial videos ('cách lên đồ tướng X') route to gameplay,
    not tutorial — gameplay sits at position 3, tutorial at position 8."""
    analysis = _analysis(
        "cách lên đồ tướng mới hướng dẫn chi tiết",
        topics=["liên quân", "gaming"],
    )
    assert classify_format(analysis, niche_id=17) == "gameplay"


# ── Wave 5+ taxonomy expansion — comedy_skit ─────────────────────────
#
# Pins the new ``comedy_skit`` bucket (position 10, before storytelling)
# added 2026-04-25 per §6.2. Two paths: strict-comedy markers fire
# regardless of niche, niche=13 markers gate the loose ``humor``/``funny``
# tokens.

def test_skit_keyword_fires_comedy_skit_regardless_of_niche() -> None:
    """Bare ``skit`` token is in comedy_strict_re — niche-agnostic."""
    analysis = _analysis(
        "Skit cuối tuần với gia đình",
        topics=["family", "skit"],
    )
    assert classify_format(analysis, niche_id=8) == "comedy_skit"


def test_prank_keyword_fires_comedy_skit() -> None:
    analysis = _analysis(
        "Prank bố mẹ giả vờ bị thương rồi cười",
        topics=["prank", "family"],
    )
    assert classify_format(analysis, niche_id=11) == "comedy_skit"


def test_niche_13_humorous_tone_fires_comedy_skit() -> None:
    """Niche 13 + tone=humorous is the n13-gated path."""
    analysis = _analysis(
        "Tình huống gia đình hài hước",
        topics=["family"],
        tone="humorous",
    )
    assert classify_format(analysis, niche_id=13) == "comedy_skit"


def test_niche_13_funny_keyword_fires_comedy_skit() -> None:
    """Loose ``funny`` token gated by niche=13."""
    analysis = _analysis(
        "Funny moments với đám trẻ trong nhà",
        topics=["funny", "kids"],
    )
    assert classify_format(analysis, niche_id=13) == "comedy_skit"


def test_funny_keyword_outside_niche_13_does_not_fire_comedy_skit() -> None:
    """Leak guard: ``funny kids`` topic on a vlog (niche 11) must NOT
    flip to comedy_skit. The n13 gate exists precisely for this."""
    analysis = _analysis(
        "Hôm nay mình quay đám trẻ trong nhà",
        topics=["funny", "kids"],
    )
    assert classify_format(analysis, niche_id=11) != "comedy_skit"


def test_bare_comedy_topic_does_not_fire_comedy_skit() -> None:
    """Leak guard: bare ``comedy`` is NOT in comedy_strict_re. Gemini
    tags fashion / vlog rows with ``comedy`` as a mood descriptor; the
    leak rate wasn't worth the coverage."""
    analysis = _analysis(
        "Outfit phối đồ đi chơi",
        topics=["fashion", "comedy"],
    )
    assert classify_format(analysis, niche_id=2) != "comedy_skit"


# ── Wave 5+ taxonomy expansion — lesson ──────────────────────────────
#
# Pins the new ``lesson`` bucket (position 9, after comparison) added
# 2026-04-25 per §6.3. Educational content WITHOUT procedural how-to
# verbs. Tone-gated (educational / authoritative) so a casual mention
# of ``vocabulary`` doesn't flip a vlog to lesson.

def test_niche_11_educational_tone_fires_lesson() -> None:
    """Niche 11 (Education) + educational tone = lesson, even without
    explicit topic keywords."""
    analysis = _analysis(
        "Today we cover the basics of supply and demand",
        topics=["economics"],
        tone="educational",
    )
    assert classify_format(analysis, niche_id=11) == "lesson"


def test_vocabulary_topic_fires_lesson_in_any_niche() -> None:
    """Lesson_topic_re matches ``vocabulary`` regardless of niche."""
    analysis = _analysis(
        "Học 10 từ vựng tiếng Anh mỗi ngày",
        topics=["vocabulary", "language learning"],
        tone="educational",
    )
    assert classify_format(analysis, niche_id=8) == "lesson"


def test_ngu_phap_routes_to_lesson() -> None:
    """Vietnamese ``ngữ pháp`` (grammar) marker."""
    analysis = _analysis(
        "Bài này nói về ngữ pháp tiếng Anh nâng cao",
        topics=["ngữ pháp"],
        tone="educational",
    )
    assert classify_format(analysis, niche_id=8) == "lesson"


def test_comparison_wins_over_lesson() -> None:
    """Priority test: ``so sánh`` + ``kinh nghiệm`` could match both
    comparison and lesson. Comparison runs at position 8, lesson at 9
    — the more-specific ``so sánh`` signal wins."""
    analysis = _analysis(
        "So sánh kinh nghiệm hai nghề khác nhau",
        topics=["career"],
        tone="educational",
    )
    assert classify_format(analysis, niche_id=11) == "comparison"


def test_lesson_requires_educational_tone() -> None:
    """Tone gate: ``vocabulary`` topic on a casual conversational row
    (e.g. a vlog about studying) must NOT flip to lesson."""
    analysis = _analysis(
        "Hôm nay mình học thêm vài từ tiếng Anh",
        topics=["vocabulary"],
        tone="conversational",
    )
    assert classify_format(analysis, niche_id=11) != "lesson"


def test_tutorial_wins_over_lesson_when_procedural_verbs_present() -> None:
    """Priority test: tutorial sits at position 8 (above lesson at 9).
    A grammar-tutorial video with ``cách``/``hướng dẫn`` should land in
    tutorial, not lesson — procedural how-to wins over passive lesson."""
    analysis = _analysis(
        "Hướng dẫn cách dùng thì hiện tại hoàn thành",
        topics=["grammar"],
        tone="educational",
    )
    assert classify_format(analysis, niche_id=11) == "tutorial"


# ── Wave 5+ taxonomy expansion — highlight ───────────────────────────
#
# Pins the new ``highlight`` bucket (position 18, last positive match)
# added 2026-04-25 per §6.4. Short music-driven reaction/moment clips.
# Niche-gated (6, 16, 17, 21) + tone-gated + scene-count + short-or-
# music transcript gate. Intentionally last so tighter buckets claim
# their rows first.

def test_niche_21_inspirational_short_clip_fires_highlight() -> None:
    """Music + inspirational tone + ≥4 scenes + short transcript = highlight.
    Uses niche 21 (Sports) — niche 6 was retired 2026-04-25 because its
    rows were dominated by showbiz aggregators rather than real creators."""
    analysis = _analysis(
        "[âm nhạc]",
        topics=["sports"],
        scenes=[{"type": "broll"}] * 5,
        tone="inspirational",
    )
    assert classify_format(analysis, niche_id=21) == "highlight"


def test_niche_16_entertaining_with_music_marker_fires_highlight() -> None:
    """Music marker passes the transcript gate even on longer raw text
    (the regex anchors on the leading ``[âm nhạc``/``[music`` token)."""
    analysis = _analysis(
        "[âm nhạc] cảnh đẹp Đà Lạt mùa hoa anh đào",
        topics=["travel", "Đà Lạt"],
        scenes=[{"type": "broll"}] * 6,
        tone="entertaining",
    )
    assert classify_format(analysis, niche_id=16) == "highlight"


def test_niche_outside_highlight_set_does_not_fire_highlight() -> None:
    """Highlight is gated to niches (6, 16, 17, 21). A niche-2 fashion
    montage with the same shape doesn't qualify."""
    analysis = _analysis(
        "[âm nhạc]",
        scenes=[{"type": "broll"}] * 5,
        tone="entertaining",
    )
    assert classify_format(analysis, niche_id=2) != "highlight"


def test_long_transcript_without_music_marker_does_not_fire_highlight() -> None:
    """Transcript >80 chars without music marker fails the gate — those
    are vlog / storytelling territory, not highlight."""
    analysis = _analysis(
        "Hôm nay mình dậy sớm để chuẩn bị cho buổi quay phim ở vùng "
        "núi phía bắc, thời tiết khá lạnh",
        scenes=[{"type": "broll"}] * 5,
        tone="entertaining",
    )
    assert classify_format(analysis, niche_id=16) != "highlight"


def test_few_scenes_does_not_fire_highlight() -> None:
    """Scene-count gate: <4 scenes is treated as a single-shot video,
    not a montage."""
    analysis = _analysis(
        "[âm nhạc]",
        scenes=[{"type": "broll"}] * 2,
        tone="inspirational",
    )
    assert classify_format(analysis, niche_id=6) != "highlight"


def test_gameplay_wins_over_highlight_for_niche_17() -> None:
    """Priority test: niche 17 is in BOTH gameplay (position 3) AND
    highlight (position 18) gates. Gameplay must win — it's the
    semantically correct bucket for gaming content."""
    analysis = _analysis(
        "[âm nhạc]",
        topics=["gaming"],
        scenes=[{"type": "action"}] * 5,
        tone="entertaining",
    )
    assert classify_format(analysis, niche_id=17) == "gameplay"
