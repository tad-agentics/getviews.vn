"""Intent enum + URL/normaliser/parser routing checks (offline, no API calls).

Pre-L1.5 this file also exercised ``classify_intent`` (deterministic
Vietnamese keyword classifier), ``destination_for_intent``,
``destination_for_gemini_primary_label``, and ``resolve_destination``.
All four were removed L1.5 audit follow-up (zero production callers
after ``/classify-intent`` removal — the report-based UX classifies
client-side via ``intent-router.ts`` and ``/stream``'s null-intent
fallback uses ``classify_intent_gemini`` directly). What remains here:
enum-membership pin, alias-normaliser contract, URL-pattern coverage,
and Vietnamese question-splitter behaviour.
"""

from __future__ import annotations

from getviews_pipeline.intents import (
    QueryIntent,
    split_into_questions,
)


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


def test_split_into_questions_vietnamese_conjunctions() -> None:
    """Vietnamese multi-question conjunctions split correctly."""
    msg = "Phân tích video này https://tiktok.com/@x/video/1. Ngoài ra, xu hướng nào đang hot?"
    parts = split_into_questions(msg)
    assert len(parts) == 2, f"Expected 2 questions, got {len(parts)}: {parts}"

    msg2 = "Video này sai gì? Thêm nữa, tôi nên làm format nào?"
    parts2 = split_into_questions(msg2)
    assert len(parts2) == 2, f"Expected 2 questions, got {len(parts2)}: {parts2}"


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
