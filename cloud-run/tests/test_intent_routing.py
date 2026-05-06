"""§19 Gate 5-style routing checks (offline, no API calls)."""

from __future__ import annotations

from getviews_pipeline.intents import (
    QueryIntent,
    classify_intent,
    extract_urls_and_handles,
    split_into_questions,
)


def test_classify_video_diagnosis() -> None:
    url = "https://www.tiktok.com/@x/video/123"
    i = classify_intent(f"Analyze this {url}", [url], [], False)
    assert i == QueryIntent.VIDEO_DIAGNOSIS


def test_classify_two_urls_fires_compare_videos() -> None:
    """Wave 4 PR #1 — two TikTok URLs → dedicated COMPARE_VIDEOS intent.
    Supersedes the retired ``series_audit``: this one has a template
    (side-by-side diagnosis) instead of silently dropping the 2nd URL."""
    urls = [
        "https://www.tiktok.com/@a/video/1",
        "https://www.tiktok.com/@a/video/2",
    ]
    msg = " ".join(urls) + " what am I doing wrong"
    i = classify_intent(msg, urls, [], False)
    assert i == QueryIntent.COMPARE_VIDEOS
    # Still must not crash AttributeError on the retired SERIES_AUDIT member.
    assert not hasattr(QueryIntent, "SERIES_AUDIT")


def test_classify_three_urls_still_compare_videos() -> None:
    """Three+ URLs also route to COMPARE_VIDEOS — the orchestrator
    caps at the first two, but the classifier doesn't need to know
    about the cap."""
    urls = [
        "https://www.tiktok.com/@a/video/1",
        "https://www.tiktok.com/@b/video/2",
        "https://www.tiktok.com/@c/video/3",
    ]
    msg = " ".join(urls)
    i = classify_intent(msg, urls, [], False)
    assert i == QueryIntent.COMPARE_VIDEOS


def test_classify_two_urls_with_keywords_still_compare_videos() -> None:
    """Two URLs must win over keyword branches — a query like
    'analyze video A vs video B' carrying both links classifies as
    COMPARE_VIDEOS, not VIDEO_DIAGNOSIS on just the first."""
    urls = [
        "https://www.tiktok.com/@a/video/1",
        "https://www.tiktok.com/@b/video/2",
    ]
    msg = f"phân tích {urls[0]} vs {urls[1]} sai ở đâu"
    i = classify_intent(msg, urls, [], False)
    assert i == QueryIntent.COMPARE_VIDEOS


def test_classify_single_url_still_video_diagnosis() -> None:
    """Sanity: one URL still hits the single-video path — the Wave 4
    branch must only trigger on ≥ 2."""
    urls = ["https://www.tiktok.com/@a/video/1"]
    msg = f"phân tích {urls[0]} tại sao flop"
    i = classify_intent(msg, urls, [], False)
    assert i == QueryIntent.VIDEO_DIAGNOSIS


def test_classify_own_flop_no_url() -> None:
    i = classify_intent("Video kênh của mình flop quá ít view", [], [], False)
    assert i == QueryIntent.OWN_FLOP_NO_URL


def test_classify_own_flop_no_url_widened_keywords() -> None:
    """2026-05-07 — widened the flop-keyword set to cover colloquial
    Vietnamese expressions that didn't route through the fast path
    before (the template-audit feedback). Each of these phrases MUST
    fire OWN_FLOP_NO_URL when paired with a "my channel / video"
    keyword."""
    # Note: keep each case free of earlier-branch keywords (e.g. "tuần
    # này" triggers TREND_SPIKE ahead of the flop check). The widening
    # is about new flop-keyword coverage, not about shuffling branch
    # priorities.
    cases = [
        "Video kênh của mình không ai xem",
        "Kênh của mình không có view",
        "Video mình ra gì đâu",
        "Kênh của tôi bết quá",
        "Video của mình kém view",
    ]
    for msg in cases:
        i = classify_intent(msg, [], [], False)
        assert i == QueryIntent.OWN_FLOP_NO_URL, (
            f"flop-widening regression for message={msg!r} — got {i}"
        )


def test_own_flop_requires_self_reference_even_with_flop_keyword() -> None:
    """A flop keyword alone must NOT fire the own_flop intent — the
    outer "my video / channel" context is required so we don't
    misclassify niche-level complaints ("ngách này bết quá")."""
    i = classify_intent("Ngách này bết quá không ai xem", [], [], False)
    assert i != QueryIntent.OWN_FLOP_NO_URL


def test_own_flop_requires_no_url() -> None:
    """URL present → video_diagnosis pipeline handles it; OWN_FLOP_NO_URL
    is specifically the fallback for URL-less flop queries."""
    url = "https://www.tiktok.com/@me/video/1"
    i = classify_intent(
        f"Video kênh của mình không ai xem {url}", [url], [], False,
    )
    assert i != QueryIntent.OWN_FLOP_NO_URL


def test_classify_competitor() -> None:
    i = classify_intent("Analyze @gymshark strategy", [], ["gymshark"], False)
    assert i == QueryIntent.COMPETITOR_PROFILE


def test_classify_brief() -> None:
    i = classify_intent("Write a brief for skincare", [], [], False)
    assert i == QueryIntent.BRIEF_GENERATION


def test_classify_trend_spike() -> None:
    i = classify_intent("What's blowing up in fitness this week?", [], [], False)
    assert i == QueryIntent.TREND_SPIKE


def test_classify_followup_with_session() -> None:
    """L1.5 — chat-era FOLLOWUP collapsed into FOLLOW_UP_UNCLASSIFIABLE.
    The deterministic classifier can't infer the subject; Gemini's
    classifiable subject can later upgrade it via the layered merge."""
    i = classify_intent("Can you elaborate on that hook pattern?", [], [], True)
    assert i == QueryIntent.FOLLOW_UP_UNCLASSIFIABLE


# ── New intent enum members (added post-foundation) ───────────────────────────


def test_query_intent_enum_has_shot_list_and_creator_search() -> None:
    """SHOT_LIST, CREATOR_SEARCH (canonical), and OWN_CHANNEL must be in
    the enum with correct values. ``FIND_CREATORS`` was removed L1.5;
    the back-compat alias lives in ``routers/intent.py:_normalize_intent_name``
    so historical sessions with intent_type=``find_creators`` still resolve."""
    assert QueryIntent.SHOT_LIST == "shot_list"
    assert QueryIntent.CREATOR_SEARCH == "creator_search"
    assert QueryIntent.OWN_CHANNEL == "own_channel"
    # Confirm Tier B values are gone from the enum.
    assert not hasattr(QueryIntent, "FIND_CREATORS")
    assert not hasattr(QueryIntent, "COMPARISON")
    assert not hasattr(QueryIntent, "FOLLOWUP")
    # L1.5 audit — METADATA_ONLY also removed (was no longer no-cost).
    assert not hasattr(QueryIntent, "METADATA_ONLY")


def test_classify_shot_list_falls_through_to_content_directions() -> None:
    """classify_intent has no shot_list keyword branch.

    A shot_list prompt without a URL and without an active session should fall
    through to CONTENT_DIRECTIONS — this is the expected behaviour until a
    dedicated keyword branch is added.  This test documents and locks in the
    current routing so any unintended change is caught.
    """
    i = classify_intent("tạo shot list cho video review mỹ phẩm", [], [], False)
    assert i == QueryIntent.CONTENT_DIRECTIONS


def test_classify_shot_list_with_session_returns_unclassifiable() -> None:
    """L1.5 — with active session and no URL, shot_list prompt falls
    through to FOLLOW_UP_UNCLASSIFIABLE (was FOLLOWUP pre-Tier-B)."""
    i = classify_intent("tạo shot list cho video review mỹ phẩm", [], [], True)
    assert i == QueryIntent.FOLLOW_UP_UNCLASSIFIABLE


# ── Short URL routing (vm.tiktok.com) ─────────────────────────────────────────


def test_short_url_vm_tiktok_routes_to_video_diagnosis() -> None:
    """vm.tiktok.com short links must route to VIDEO_DIAGNOSIS, not COMPETITOR_PROFILE.

    Short URLs have no /video/ path segment and no @handle — they redirect to
    the full video URL server-side.  The classifier must not mistake them for
    profile (competitor) URLs.
    """
    url = "https://vm.tiktok.com/ZMrXYZ123/"
    urls, handles = extract_urls_and_handles(url)
    assert urls == [url], "short URL must be extracted by _TIKTOK_URL_RE"
    assert handles == [], "short URL must not produce a handle"
    i = classify_intent(url, urls, handles, False)
    assert i == QueryIntent.VIDEO_DIAGNOSIS, (
        f"short vm.tiktok.com URL should be VIDEO_DIAGNOSIS, got {i}"
    )


def test_short_url_with_diagnostic_text_routes_to_video_diagnosis() -> None:
    """Short URL pasted with Vietnamese diagnostic text → VIDEO_DIAGNOSIS."""
    url = "https://vm.tiktok.com/ZMrXYZ123/"
    msg = f"tại sao video này ít view {url}"
    urls, handles = extract_urls_and_handles(msg)
    i = classify_intent(msg, urls, handles, False)
    assert i == QueryIntent.VIDEO_DIAGNOSIS


# ── Vietnamese keyword routing ────────────────────────────────────────────────


def test_classify_vietnamese_video_diagnosis_with_url() -> None:
    """Vietnamese diagnostic phrases + URL → VIDEO_DIAGNOSIS."""
    url = "https://www.tiktok.com/@x/video/123"
    for phrase in [
        f"tại sao video này ít view {url}",
        f"phân tích video {url}",
        f"video này sai ở đâu {url}",
    ]:
        urls, handles = extract_urls_and_handles(phrase)
        i = classify_intent(phrase, urls, handles, False)
        assert i == QueryIntent.VIDEO_DIAGNOSIS, f"Expected VIDEO_DIAGNOSIS for: {phrase!r}, got {i}"


def test_classify_vietnamese_trend_spike() -> None:
    """Vietnamese trend signals → TREND_SPIKE."""
    for phrase in [
        "video nào đang hot tuần này trong fitness",
        "xu hướng nào đang lên trong mỹ phẩm",
        "content nào đang viral hôm nay",
    ]:
        i = classify_intent(phrase, [], [], False)
        assert i == QueryIntent.TREND_SPIKE, f"Expected TREND_SPIKE for: {phrase!r}, got {i}"


def test_classify_kieu_quay_routes_content_directions_before_trend() -> None:
    """'Kiểu quay … đang lên' must not fall through to TREND_SPIKE."""
    phrase = (
        "Kiểu quay (POV, lồng tiếng, list, storytime) nào đang lên view nhanh trong gym?"
    )
    assert classify_intent(phrase, [], [], False) == QueryIntent.CONTENT_DIRECTIONS


def test_classify_chu_de_goc_ke_tuan_nay_trend_spike() -> None:
    """Studio Home topic chip → TREND_SPIKE."""
    phrase = "Chủ đề và góc kể nào đang hot trong gym tuần này?"
    assert classify_intent(phrase, [], [], False) == QueryIntent.TREND_SPIKE


def test_classify_vietnamese_brief_generation() -> None:
    """Vietnamese brief signals → BRIEF_GENERATION."""
    for phrase in [
        "viết brief cho video skincare tuần tới",
        "tạo brief nội dung cho kênh fitness",
        "lên kế hoạch content cho tháng này",
    ]:
        i = classify_intent(phrase, [], [], False)
        assert i == QueryIntent.BRIEF_GENERATION, f"Expected BRIEF_GENERATION for: {phrase!r}, got {i}"


def test_classify_vietnamese_content_directions() -> None:
    """Vietnamese direction signals (no URL) → CONTENT_DIRECTIONS."""
    for phrase in [
        "nên làm video gì trong niche skincare",
        "ý tưởng video nào đang hoạt động tốt",
        "hướng nội dung nào phù hợp",
    ]:
        i = classify_intent(phrase, [], [], False)
        assert i == QueryIntent.CONTENT_DIRECTIONS, f"Expected CONTENT_DIRECTIONS for: {phrase!r}, got {i}"


def test_split_into_questions_vietnamese_conjunctions() -> None:
    """Vietnamese multi-question conjunctions split correctly."""
    msg = "Phân tích video này https://tiktok.com/@x/video/1. Ngoài ra, xu hướng nào đang hot?"
    parts = split_into_questions(msg)
    assert len(parts) == 2, f"Expected 2 questions, got {len(parts)}: {parts}"

    msg2 = "Video này sai gì? Thêm nữa, tôi nên làm format nào?"
    parts2 = split_into_questions(msg2)
    assert len(parts2) == 2, f"Expected 2 questions, got {len(parts2)}: {parts2}"


def test_profile_url_without_video_routes_to_video_diagnosis_not_competitor() -> None:
    """/@handle profile URL: has_urls=True overrides the competitor guard.

    classify_intent line 114: `if handles and not has_urls` — since the profile
    URL matches _TIKTOK_URL_RE, has_urls=True and the guard is skipped.
    The fallthrough at line 189 then returns VIDEO_DIAGNOSIS.

    This documents current Python behaviour.  If a dedicated profile-URL
    detector is added later, update this test.
    """
    url = "https://www.tiktok.com/@gymshark"
    urls, handles = extract_urls_and_handles(url)
    assert urls, "profile URL must still be captured by _TIKTOK_URL_RE"
    # Handles are extracted after URL strip; bare profile URL may yield no standalone @handle.
    i = classify_intent(url, urls, handles, False)
    # has_urls=True skips competitor guard → VIDEO_DIAGNOSIS fallthrough
    assert i == QueryIntent.VIDEO_DIAGNOSIS


# -----------------------------------------------------------------------------
# follow_up_classifiable subject routing (2026-05-07)
# -----------------------------------------------------------------------------


def test_follow_up_classifiable_routes_original_three_subjects() -> None:
    """Regression guard for the historical subject set — lifecycle +
    diagnostic were added later, but pattern/ideas/timing must still
    route correctly."""
    from getviews_pipeline.intent_router import resolve_destination

    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject="pattern",
    ) == "answer:pattern"
    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject="ideas",
    ) == "answer:ideas"
    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject="timing",
    ) == "answer:timing"


def test_follow_up_classifiable_routes_lifecycle_subject() -> None:
    """Follow-up classified as ``lifecycle`` lands on ``answer:lifecycle``
    instead of being dropped (returning None and falling through to the
    generic shelf)."""
    from getviews_pipeline.intent_router import resolve_destination

    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject="lifecycle",
    ) == "answer:lifecycle"


def test_follow_up_classifiable_routes_diagnostic_subject() -> None:
    from getviews_pipeline.intent_router import resolve_destination

    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject="diagnostic",
    ) == "answer:diagnostic"


def test_follow_up_classifiable_unknown_subject_returns_none() -> None:
    """Defence in depth: an off-script subject string must yield None
    (callers then downgrade to the generic answer shelf) rather than
    constructing ``answer:<garbage>``."""
    from getviews_pipeline.intent_router import resolve_destination

    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject="weird_value",
    ) is None
    assert resolve_destination(
        "follow_up_classifiable", follow_up_subject=None,
    ) is None


# ── Wave 4 PR #1 — compare_videos destination ───────────────────────────

def test_compare_videos_routes_to_compare_destination() -> None:
    """Keyword-path mapping: ``compare_videos`` routes to the top-level
    ``compare`` destination (mirrors ``video`` — URL-bearing, dedicated
    screen + /stream, NOT the niche-scoped ``answer:`` session shelf).
    Pinned on both entry points: ``INTENT_TO_DESTINATION`` (fast-path)
    and ``_GEMINI_PRIMARY_TO_DESTINATION`` (slow-path classifier)."""
    from getviews_pipeline.intent_router import (
        destination_for_gemini_primary_label,
        destination_for_intent,
    )

    assert destination_for_intent(QueryIntent.COMPARE_VIDEOS.value) == "compare"
    assert destination_for_gemini_primary_label("compare_videos") == "compare"


# ── L1.5 Tier B back-compat aliases ─────────────────────────────────────


def test_legacy_intent_strings_normalise_to_current_values() -> None:
    """Historical session intent_type strings (Tier B removed enums) must
    still resolve via the router-edge alias normaliser. Without these
    aliases, /intent endpoint requests carrying legacy strings (or
    Gemini cached classifier outputs) would fail validation downstream."""
    from getviews_pipeline.routers.intent import _normalize_intent_name

    # FIND_CREATORS removed in L1.5 → folds into canonical CREATOR_SEARCH.
    assert _normalize_intent_name("find_creators") == "creator_search"
    # COMPARISON removed → folds into COMPETITOR_PROFILE (where it used to
    # alias). Historical session preview rounds still resolve.
    assert _normalize_intent_name("comparison") == "competitor_profile"
    # FOLLOWUP removed → folds into the modern unclassifiable surface
    # (was previously normalised to "follow_up" which is a Gemini label,
    # not an enum value).
    assert _normalize_intent_name("followup") == "follow_up_unclassifiable"
    # METADATA_ONLY removed L1.5 audit — historical session rows fold into
    # the generic-fallback path (which is what the FE comment used to
    # promise but didn't actually deliver).
    assert _normalize_intent_name("metadata_only") == "follow_up_unclassifiable"
    # Sanity: unrelated values pass through unchanged.
    assert _normalize_intent_name("video_diagnosis") == "video_diagnosis"
    assert _normalize_intent_name(None) is None


# ── L1.5 audit: shared TIKTOK_URL_RE consolidation ────────────────────────


def test_canonical_tiktok_url_re_matches_all_subdomains() -> None:
    """The shared pattern must match every short-link subdomain TikTok ships.
    Pre-L1.5, ``report_video.py`` had its own regex missing ``vt.tiktok.com``,
    so a vt-link could classify as video_diagnosis (intents.py matched it)
    and then fail extraction in the report builder — silent dead-end."""
    from getviews_pipeline.url_patterns import TIKTOK_URL_RE

    cases = [
        "https://www.tiktok.com/@user/video/123",
        "https://tiktok.com/@user/video/123",
        "https://m.tiktok.com/v/123",
        "https://vm.tiktok.com/abc123",
        "https://vt.tiktok.com/abc123",  # critical — was missing in report_video.py
        "http://www.tiktok.com/@user/video/123",  # http (rare but valid)
    ]
    for url in cases:
        assert TIKTOK_URL_RE.search(url), f"Failed to match: {url}"


def test_canonical_tiktok_url_re_used_by_both_be_callers() -> None:
    """``intents.py`` and ``report_video.py`` must share the same compiled
    pattern — drift is exactly what L1.5 fixed."""
    from getviews_pipeline.intents import _TIKTOK_URL_RE as intents_re
    from getviews_pipeline.report_video import _TIKTOK_URL_RE as report_re
    from getviews_pipeline.url_patterns import TIKTOK_URL_RE

    assert intents_re is TIKTOK_URL_RE
    assert report_re is TIKTOK_URL_RE
