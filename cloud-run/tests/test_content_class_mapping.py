"""Tests for ``_content_class_for`` — Python mirror of the SQL backfill.

Both the Python helper (used by the live ingest pipeline) and
``map_legacy_corpus_to_content_class`` (used by the one-shot SQL
backfill in 20260511000000_two_axis_niche_pr2_corpus.sql) must produce
the same result for any (legacy_niche_id, content_format) pair so
mid-deploy half-state corpus rows stay consistent.

These tests pin the Python side. The SQL side is exercised by manual
review of the migration (no live DB in unit-test env). When updating
the mapping, change BOTH sides in lock-step.
"""

from __future__ import annotations

import pytest


def _f():
    """Lazy-import so ``pydantic`` etc. don't load at collection time."""
    try:
        from getviews_pipeline.corpus_ingest import _content_class_for
        return _content_class_for
    except ModuleNotFoundError:
        pytest.skip("pydantic not installed in test env")


@pytest.mark.parametrize(
    "niche_id,content_format,expected",
    [
        # Beauty
        (2, "review", 3),
        (2, "haul", 4),
        (2, "tutorial", 1),
        (2, "grwm", 2),
        (2, "before_after", 5),
        (2, "other", 1),  # default
        # Fashion
        (3, "haul", 7),
        (3, "review", 8),
        (3, "outfit_transition", 9),
        (3, "vlog", 10),
        (3, "other", 6),
        # Food
        (4, "recipe", 13),
        (4, "mukbang", 14),
        (4, "review", 11),
        (4, "vlog", 12),
        (4, "other", 11),
        # Business / Finance
        (5, "haul", 49),
        (5, "tutorial", 48),
        (5, "storytelling", 47),
        (5, "other", 48),
        (10, "anything", 51),
        (15, "storytelling", 47),
        (15, "comparison", 46),
        (15, "other", 45),
        # Family
        (7, "comedy_skit", 31),
        (7, "vlog", 30),
        (7, "lesson", 33),
        (7, "other", 33),
        # Education
        (11, "lesson", 36),
        (11, "tutorial", 37),
        (11, "storytelling", 38),
        (11, "other", 35),
        # Tech / Gaming
        (9, "haul", 40),
        (9, "tutorial", 41),
        (9, "other", 40),
        (17, "gameplay", 42),
        (17, "review", 43),
        (17, "other", 42),
        # Comedy / Music
        (13, "comedy_skit", 24),
        (13, "dance", 29),
        (13, "storytelling", 26),
        (13, "other", 24),
        (22, "dance", 29),
        (22, "other", 28),
        # Auto
        (14, "review", 65),
        (14, "tutorial", 67),
        (14, "vlog", 66),
        (14, "other", 65),
        (25, "review", 65),  # legacy moto
        # Travel & Sports
        (16, "lesson", 62),
        (16, "highlight", 63),
        (16, "other", 60),
        (21, "highlight", 64),
        (21, "vlog", 63),
        (21, "other", 64),
        # Gym / Fitness
        (8, "vlog", 59),
        (8, "tutorial", 56),
        (8, "other", 56),
        # Wellness
        (26, "vlog", 55),
        (26, "lesson", 53),
        (26, "other", 52),
        # Pets
        (19, "tutorial", 71),
        (19, "lesson", 70),
        (19, "storytelling", 72),
        (19, "other", 72),
        # Home
        (20, "tutorial", 74),
        (20, "haul", 73),
        (20, "other", 73),
        # Retired-niche fallthrough
        (1, "anything", 49),
        (6, "anything", 23),
        (12, "anything", 50),
        (18, "anything", 13),
        (24, "anything", 46),
        # Unknown / null
        (999, "tutorial", None),
    ],
)
def test_mapping(niche_id: int, content_format: str, expected: int | None) -> None:
    f = _f()
    assert f(niche_id, content_format) == expected


def test_null_inputs() -> None:
    f = _f()
    assert f(None, "tutorial") is None  # type: ignore[arg-type]
    assert f(2, None) == 1  # niche default still applies when format unknown
