"""Tests for the ``iter_awemes_from_search_payload`` envelope parser.

The parser was originally written for keyword/hashtag search responses
(``data.data`` is the list). When ``fetch_user_posts`` started routing
its responses through it (TikTok user/posts envelope uses
``data.aweme_list``), every call silently returned ``[]`` — which is
why CreatorComparison was unreachable in production for 14 days
despite the gate fix.

The 2026-05-08 fix accepts both shapes. These tests pin both.
"""

from __future__ import annotations

import logging

import pytest

from getviews_pipeline.ensemble import iter_awemes_from_search_payload


def _aweme(aid: str) -> dict[str, object]:
    return {"aweme_id": aid, "video": {"play_addr": {"url_list": []}}}


def test_parses_keyword_search_envelope() -> None:
    """``data.data`` shape — keyword/hashtag search. Must keep working."""
    payload = {"data": [_aweme("a"), _aweme("b")]}
    out = iter_awemes_from_search_payload(payload)
    assert [a["aweme_id"] for a in out] == ["a", "b"]


def test_parses_user_posts_envelope_with_aweme_list() -> None:
    """``data.aweme_list`` shape — TikTok user/posts (legacy
    ``new_version=False``). Was the silent breakage path before
    2026-05-08."""
    payload = {"aweme_list": [_aweme("x"), _aweme("y")], "has_more": 1}
    out = iter_awemes_from_search_payload(payload)
    assert [a["aweme_id"] for a in out] == ["x", "y"]


def test_aweme_list_takes_precedence_over_data_when_both_present() -> None:
    """Some hybrid envelopes may carry both. ``aweme_list`` is the
    canonical TikTok feed key, so prefer it."""
    payload = {
        "aweme_list": [_aweme("a")],
        "data": [_aweme("b")],
    }
    out = iter_awemes_from_search_payload(payload)
    assert [a["aweme_id"] for a in out] == ["a"]


def test_bare_list_passes_through() -> None:
    """Some endpoints return the list at the top level."""
    out = iter_awemes_from_search_payload([_aweme("z")])
    assert [a["aweme_id"] for a in out] == ["z"]


def test_unknown_envelope_logs_top_keys(caplog: pytest.LogCaptureFixture) -> None:
    """When neither ``aweme_list`` nor ``data`` resolves to a list,
    log the top-level keys so a future ED contract change is
    diagnosable from Cloud Run logs without redeploys."""
    payload = {"results": [_aweme("a")], "stats": {}}
    with caplog.at_level(logging.INFO, logger="getviews_pipeline.ensemble"):
        out = iter_awemes_from_search_payload(payload)
    assert out == []
    assert any(
        "unexpected feed payload shape" in rec.message
        and "results" in rec.message
        for rec in caplog.records
    )


def test_none_payload_returns_empty_list() -> None:
    assert iter_awemes_from_search_payload(None) == []


def test_filters_items_without_aweme_id_or_video() -> None:
    """Only items shaped like an aweme should pass through."""
    payload = {"aweme_list": [{"aweme_id": "good"}, {"unrelated": "junk"}]}
    out = iter_awemes_from_search_payload(payload)
    assert [a["aweme_id"] for a in out] == ["good"]
