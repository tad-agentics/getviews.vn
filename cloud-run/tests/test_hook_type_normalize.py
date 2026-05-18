"""Parity tests for ``normalize_hook_type`` (TikTok + Douyin + §8 matcher)."""

from __future__ import annotations

from getviews_pipeline.hook_type_normalize import normalize_hook_type


def test_empty_becomes_other() -> None:
    assert normalize_hook_type("") == "other"
    assert normalize_hook_type(None) == "other"


def test_english_aliases() -> None:
    assert normalize_hook_type("tutorial") == "how_to"
    assert normalize_hook_type("Tutorial") == "how_to"
    assert normalize_hook_type("story-telling") == "story_open"


def test_vietnamese_aliases() -> None:
    assert normalize_hook_type("huong_dan") == "how_to"
    assert normalize_hook_type("canh_bao") == "warning"


def test_canonical_pass_through() -> None:
    assert normalize_hook_type("curiosity_gap") == "curiosity_gap"
    assert normalize_hook_type("question") == "question"


def test_unknown_becomes_other() -> None:
    assert normalize_hook_type("not_a_real_hook") == "other"
