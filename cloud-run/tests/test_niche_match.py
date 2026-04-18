"""Regression tests for free-text niche inference (P0-1).

The failing input from the 2026-04-18 content_directions audit:
    "review đồ skincare Hàn Quốc cho da dầu mụn, target khách hàng 18-25 tuổi"

Before the fix this string passed through as the niche name, never matched
niche_taxonomy, and the pipeline fell back to live keyword search returning
off-domain references. These tests use a fake Supabase client that returns a
canned taxonomy so the matcher is exercised without any network calls.
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline import niche_match


# ---------------------------------------------------------------------------
# Fake Supabase client — returns a canned niche_taxonomy table.
# ---------------------------------------------------------------------------

_TAXONOMY = [
    {"id": 1, "name_en": "Skincare", "name_vn": "làm đẹp", "signal_hashtags": ["#skincare", "#beauty"]},
    {"id": 2, "name_en": "Fitness", "name_vn": "thể hình", "signal_hashtags": ["#gym", "#workout"]},
    {"id": 3, "name_en": "Cooking", "name_vn": "nấu ăn", "signal_hashtags": ["#recipe", "#nauan"]},
    {"id": 4, "name_en": "Home goods review", "name_vn": "review đồ gia dụng", "signal_hashtags": ["#giadung"]},
    {"id": 5, "name_en": "Fashion", "name_vn": "thời trang", "signal_hashtags": ["#ootd"]},
]


class _FakeResult:
    def __init__(self, data: Any) -> None:
        self.data = data


class _FakeTable:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def select(self, *_a: Any, **_k: Any) -> "_FakeTable":
        return self

    def execute(self) -> _FakeResult:
        return _FakeResult(self._rows)


class _FakeClient:
    def table(self, name: str) -> _FakeTable:
        assert name == "niche_taxonomy"
        return _FakeTable(_TAXONOMY)


def _setup_module_cache() -> None:
    # Force a fresh taxonomy fetch for each test.
    niche_match._invalidate_taxonomy_cache()


def test_matches_skincare_from_vietnamese_prose() -> None:
    _setup_module_cache()
    q = "review đồ skincare Hàn Quốc cho da dầu mụn, target khách hàng 18-25 tuổi"
    m = niche_match.find_niche_match(_FakeClient(), q)
    assert m is not None
    assert m.niche_id == 1
    assert m.label == "làm đẹp"
    assert m.matched_on == "hashtag"
    assert m.matched_token == "skincare"


def test_matches_name_vn_substring() -> None:
    _setup_module_cache()
    q = "mấy video review đồ gia dụng tuần này hot không"
    m = niche_match.find_niche_match(_FakeClient(), q)
    assert m is not None
    assert m.niche_id == 4
    assert m.label == "review đồ gia dụng"
    assert m.matched_on == "name_vn"


def test_matches_without_diacritics() -> None:
    _setup_module_cache()
    # User typed without Vietnamese tone marks — matcher must fold both sides.
    q = "lam dep cho da dau mun"
    m = niche_match.find_niche_match(_FakeClient(), q)
    assert m is not None
    assert m.niche_id == 1


def test_returns_none_when_no_match() -> None:
    _setup_module_cache()
    q = "hôm nay trời đẹp quá nhỉ"
    m = niche_match.find_niche_match(_FakeClient(), q)
    assert m is None


def test_empty_query_returns_none() -> None:
    _setup_module_cache()
    assert niche_match.find_niche_match(_FakeClient(), "") is None
    assert niche_match.find_niche_match(_FakeClient(), "   ") is None


def test_stopword_does_not_cause_false_match() -> None:
    _setup_module_cache()
    # "review" alone is a stopword — it must NOT match the "review đồ gia dụng" niche
    # on its own. The test query talks about news, not home goods.
    q = "review show truyền hình hôm nay"
    m = niche_match.find_niche_match(_FakeClient(), q)
    # "review đồ gia dụng" requires the full phrase; bare "review" shouldn't hit.
    assert m is None or m.niche_id != 4
