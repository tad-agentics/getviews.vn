"""Sprint 8.5 — creator_blocklist.is_blocklisted_handle contract.

Pins the case-insensitive, @-tolerant lookup so a future blocklist
edit can't silently let a known media account back in OR
accidentally block a legitimate creator.
"""

from __future__ import annotations

import pytest

from getviews_pipeline.creator_blocklist import (
    NEWS_AGGREGATOR_HANDLES,
    is_blocklisted_handle,
)

# ── Known-blocked accounts (must stay blocked) ──────────────────────────


@pytest.mark.parametrize(
    "handle",
    [
        # theanh28 family
        "theanh28gaming", "theanh28sport", "hanoinews.theanh28",
        # vtvcab variants
        "vtvcab", "vtvcab.tintuc", "vtvcab.gaming.onlive",
        # 24h family
        "24h.sports", "bongda24h.vn.official",
        # major news / showbiz
        "kenh14official", "znewssocial", "beatvn_official",
        "vnexpress_hanoi", "vietnamnet.vn",
        # sports outlets
        "thethao247.vn", "football.century_", "onsportsplus",
        "fptplay.sports", "fptplay.bongdaviet", "bongdavadoisong",
        # general news
        "28international",
        # gaming/esports news
        "kiran.aov.news", "vovgamesport",
    ],
)
def test_known_handles_are_blocklisted(handle: str) -> None:
    assert is_blocklisted_handle(handle) is True


def test_at_prefix_is_normalised() -> None:
    """Incoming awemes from EnsembleData may carry the leading @."""
    assert is_blocklisted_handle("@theanh28sport") is True
    assert is_blocklisted_handle("@vtvcab.tintuc") is True


def test_case_insensitive() -> None:
    """corpus stores lowercase, but be defensive."""
    assert is_blocklisted_handle("THEANH28GAMING") is True
    assert is_blocklisted_handle("VTVCab.Sports") is True


def test_whitespace_tolerant() -> None:
    assert is_blocklisted_handle("  theanh28sport  ") is True


# ── Legitimate creators (must NOT be blocked) ───────────────────────────


@pytest.mark.parametrize(
    "handle",
    [
        # Real creators we've already analyzed in the corpus
        "harry.nista",          # fashion creator (Sprint 8 unblocked him)
        "learnvietwithtu",      # Vietnamese language teacher
        "kimthichnhacua",       # personal creator
        "anhbu_2912",           # student/comedy creator
        "nguyenxuanhung1997",   # wordplay reaction creator
        "skanskin.em",          # skincare creator
        # Personal handles that *look* news-y but aren't (single-creator
        # accounts with `.vn` or `.news` style suffixes)
        "lanhuyen.nha.dat.uy.tin",   # real estate creator
        "mai.ting.anh.thivao10",     # education student
        "hsv_hvtc",                  # finance student
    ],
)
def test_legitimate_creators_not_blocklisted(handle: str) -> None:
    assert is_blocklisted_handle(handle) is False


# ── Defensive / edge cases ──────────────────────────────────────────────


@pytest.mark.parametrize("falsy", [None, "", "   ", "@", "@@@"])
def test_falsy_inputs_return_false(falsy: str | None) -> None:
    assert is_blocklisted_handle(falsy) is False


def test_non_string_input_returns_false() -> None:
    """Defensive against malformed aweme payloads where unique_id is
    sometimes ``None`` or, very rarely, an int."""
    assert is_blocklisted_handle(12345) is False  # type: ignore[arg-type]
    assert is_blocklisted_handle({"unique_id": "x"}) is False  # type: ignore[arg-type]


def test_blocklist_entries_are_normalised_lowercase_no_at() -> None:
    """Invariant — every entry in the constant must be lowercased and
    leading-@-stripped, otherwise the lookup misses on equivalent input."""
    for h in NEWS_AGGREGATOR_HANDLES:
        assert h == h.lower(), f"non-lowercase entry: {h!r}"
        assert not h.startswith("@"), f"entry must not start with @: {h!r}"


def test_blocklist_has_no_duplicates_across_clusters() -> None:
    """A frozenset can't have duplicates by construction; this
    assertion is a regression guard if the literal is later refactored
    into a list/tuple of multiple sources merged together."""
    assert len(NEWS_AGGREGATOR_HANDLES) == len(set(NEWS_AGGREGATOR_HANDLES))
    # Sanity check — Sprint 8.5 ships ~85 entries; alert if a future
    # refactor accidentally truncates the list.
    assert len(NEWS_AGGREGATOR_HANDLES) >= 80
