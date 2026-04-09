"""§19 Gate 5-style routing checks (offline, no API calls)."""

from __future__ import annotations

from getviews_pipeline.intents import (
    QueryIntent,
    check_chain_dependencies,
    classify_intent,
    collapse_to_intents,
    detect_hybrid_intents,
    extract_per_question,
    extract_urls_and_handles,
    is_knowledge_question,
    split_into_questions,
)
from getviews_pipeline.session_store import (
    fresh_session_context,
    get_session_context,
    record_knowledge_turn,
    reset_session,
)


def test_classify_video_diagnosis() -> None:
    url = "https://www.tiktok.com/@x/video/123"
    i = classify_intent(f"Analyze this {url}", [url], [], False)
    assert i == QueryIntent.VIDEO_DIAGNOSIS


def test_classify_series_audit_multi_url() -> None:
    urls = [
        "https://www.tiktok.com/@a/video/1",
        "https://www.tiktok.com/@a/video/2",
    ]
    msg = " ".join(urls) + " what am I doing wrong"
    i = classify_intent(msg, urls, [], False)
    assert i == QueryIntent.SERIES_AUDIT


def test_classify_competitor() -> None:
    i = classify_intent("Analyze @gymshark strategy", [], ["gymshark"], False)
    assert i == QueryIntent.COMPETITOR_PROFILE


def test_classify_brief() -> None:
    i = classify_intent("Write a brief for skincare", [], [], False)
    assert i == QueryIntent.BRIEF_GENERATION


def test_classify_trend_spike() -> None:
    i = classify_intent("What's blowing up in fitness this week?", [], [], False)
    assert i == QueryIntent.TREND_SPIKE


def test_classify_metadata_only() -> None:
    url = "https://www.tiktok.com/@x/video/9"
    i = classify_intent(f"How many views on {url}", [url], [], False)
    assert i == QueryIntent.METADATA_ONLY


def test_classify_followup_with_session() -> None:
    i = classify_intent("Can you elaborate on that hook pattern?", [], [], True)
    assert i == QueryIntent.FOLLOWUP


def test_knowledge_no_url() -> None:
    assert is_knowledge_question("Does the algorithm punish deleting videos?")


def test_rule_a_url_guard_uses_message_level_urls() -> None:
    """§3a: knowledge pre-filter is skipped when any URL is present (server checks ``not urls``)."""
    url = "https://www.tiktok.com/@x/video/1"
    msg = f"Does the algorithm favor this? {url}"
    urls, _ = extract_urls_and_handles(msg)
    assert urls
    assert is_knowledge_question(msg)
    assert not (not urls and is_knowledge_question(msg))


def test_hybrid_trend_and_directions() -> None:
    h = detect_hybrid_intents(
        "What hooks are working right now in fitness?",
        [],
        [],
    )
    assert h == [QueryIntent.TREND_SPIKE, QueryIntent.CONTENT_DIRECTIONS]


def test_hybrid_url_and_handle() -> None:
    url = "https://www.tiktok.com/@u/video/1"
    h = detect_hybrid_intents(
        f"Why flop vs @gymshark? {url}",
        [url],
        ["gymshark"],
    )
    assert h == [QueryIntent.COMPETITOR_PROFILE, QueryIntent.VIDEO_DIAGNOSIS]


def test_collapse_url_isolation_between_questions() -> None:
    url = "https://www.tiktok.com/@u/video/1"
    msg = f"Analyze {url}. Also, what's trending in fitness?"
    qs = split_into_questions(msg)
    collapsed = collapse_to_intents(qs, [], [], False)
    intents_found = [p[0] for p in collapsed.pairs]
    assert QueryIntent.VIDEO_DIAGNOSIS in intents_found
    assert (
        QueryIntent.TREND_SPIKE in intents_found
        or QueryIntent.CONTENT_DIRECTIONS in intents_found
    )


def test_chain_brief_dependencies_empty_session() -> None:
    ctx = fresh_session_context()
    missing = check_chain_dependencies(QueryIntent.BRIEF_GENERATION, ctx, handles=None)
    assert QueryIntent.CONTENT_DIRECTIONS in missing
    assert QueryIntent.VIDEO_DIAGNOSIS in missing


def test_extract_per_question_no_cross_leak() -> None:
    url = "https://www.tiktok.com/@a/video/1"
    q1, q2 = extract_per_question("Trending fitness?"), extract_per_question(f"See {url}")
    assert q1[0] == [] and q2[0] == [url]


def test_record_knowledge_turn_idempotent_completed() -> None:
    ctx = fresh_session_context()
    record_knowledge_turn(ctx)
    record_knowledge_turn(ctx)
    assert ctx["completed_intents"] == ["knowledge"]
    assert ctx["analyses_summary"]["intents_run"] == ["knowledge"]


def test_collapse_collects_knowledge_questions() -> None:
    """Knowledge sub-questions are collected, not silently dropped."""
    msg = "Does the algorithm punish posting? Also, what's trending in fitness?"
    qs = split_into_questions(msg)
    collapsed = collapse_to_intents(qs, [], [], False)
    assert len(collapsed.knowledge_questions) >= 1
    assert any("algorithm" in q.lower() for q in collapsed.knowledge_questions)
    assert len(collapsed.pairs) >= 1


def test_collapse_all_knowledge_returns_empty_pairs() -> None:
    """When every question is knowledge-only, pairs is empty."""
    msg = "Does the algorithm punish deleting? Also, how does shadowban work?"
    qs = split_into_questions(msg)
    collapsed = collapse_to_intents(qs, [], [], False)
    assert collapsed.pairs == []
    assert len(collapsed.knowledge_questions) >= 2


def test_classify_metadata_only_not_blocked_by_what() -> None:
    """The 'what' keyword no longer blocks METADATA_ONLY routing."""
    url = "https://www.tiktok.com/@x/video/9"
    i = classify_intent(f"What are the stats on {url}", [url], [], False)
    assert i == QueryIntent.METADATA_ONLY


def test_classify_what_should_overrides_metadata() -> None:
    """'what should' routes to VIDEO_DIAGNOSIS, not METADATA_ONLY."""
    url = "https://www.tiktok.com/@x/video/9"
    i = classify_intent(
        f"What should I fix on this {url} stats are bad", [url], [], False
    )
    assert i == QueryIntent.VIDEO_DIAGNOSIS


def test_niche_inference_strips_urls() -> None:
    from getviews_pipeline.intents import infer_niche_from_message

    niche = infer_niche_from_message(
        "Analyze this video https://tiktok.com/@user/video/123"
    )
    assert "tiktok.com" not in niche
    assert "https" not in niche


def test_reset_session_clears_context() -> None:
    sid = "test-reset-session"
    reset_session(sid)
    s = get_session_context(sid)
    s["completed_intents"].append("video_diagnosis")
    s["niche"] = "fitness"
    reset_session(sid)
    s2 = get_session_context(sid)
    assert s2["completed_intents"] == []
    assert s2["niche"] is None
