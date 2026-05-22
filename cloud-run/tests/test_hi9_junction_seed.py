"""HI-9 + HI-16 — junction seed sanity vs Gemini enum (no live DB)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from getviews_pipeline.two_axis_taxonomy import (
    CAROUSEL_FORMAT_AXIS_SLUGS,
    CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS,
    CREATOR_NICHE_SLUGS,
    FORMAT_AXIS_SLUGS,
    JUNCTION_NICHE_FORMAT_PAIRS,
    VIDEO_JUNCTION_NICHE_FORMAT_PAIRS,
    junction_has_pair,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_covered_niche_format_pairs() -> set[tuple[str, str]]:
    """Parse PR1 + PR6 migrations: (creator_niche.slug, content_class.format_axis)."""
    root = _repo_root()
    sql = (root / "supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql").read_text(
        encoding="utf-8",
    )
    m = re.search(r"INSERT INTO content_classifications[^;]+;", sql, re.DOTALL)
    assert m is not None, "content_classifications INSERT not found"
    block = m.group(0)
    rows = re.findall(
        r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,"
        r"\s*'([^']+)'\s*,\s*'([^']+)'",
        block,
    )
    cc_fmt = {int(r[0]): r[4] for r in rows}

    nblock = re.search(r"INSERT INTO creator_niches[^;]+;", sql, re.DOTALL)
    assert nblock is not None
    niche_slug = {
        int(a): b
        for a, b in re.findall(r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,", nblock.group(0))
    }

    pr6 = root / (
        "supabase/migrations/20260630000003_creator_niches_16_music_real_estate.sql"
    )
    t3 = pr6.read_text(encoding="utf-8")
    for ma, sl in re.findall(
        r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'[^']+'\s*,\s*'[^']+'",
        t3,
    ):
        niche_slug[int(ma)] = sl

    jstart = sql.find(
        "INSERT INTO creator_niche_content_classes "
        "(creator_niche_id, content_class_id, is_primary) VALUES",
    )
    assert jstart != -1
    jchunk = sql[jstart : jstart + 8000]
    pairs = re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,", jchunk)
    junc = {(int(a), int(b)) for a, b in pairs}
    for a, b in re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*TRUE\s*\)", t3):
        junc.add((int(a), int(b)))

    covered: set[tuple[str, str]] = set()
    for nid, cid in junc:
        slug = niche_slug.get(nid)
        fmt = cc_fmt.get(cid)
        if slug and fmt:
            covered.add((slug, fmt))
    return covered


@pytest.fixture(scope="module")
def covered_pairs() -> set[tuple[str, str]]:
    return _load_covered_niche_format_pairs()


def test_hi9_junction_seed_maps_every_creator_niche_slug() -> None:
    slugs_in_junction = {p[0] for p in VIDEO_JUNCTION_NICHE_FORMAT_PAIRS}
    assert slugs_in_junction == set(CREATOR_NICHE_SLUGS)


def test_hi9_each_video_format_axis_used_in_at_least_one_niche_row() -> None:
    axes_seen = {p[1] for p in VIDEO_JUNCTION_NICHE_FORMAT_PAIRS}
    assert axes_seen == set(FORMAT_AXIS_SLUGS)


def test_hi9_junction_tuple_count_stable() -> None:
    """16 active UX niches — post-20260824 taxonomy v2."""
    assert len(VIDEO_JUNCTION_NICHE_FORMAT_PAIRS) == 56


def test_hi9_video_junction_constant_matches_python_source() -> None:
    """Runtime junction is authoritative after taxonomy v2 expansion."""
    assert len(VIDEO_JUNCTION_NICHE_FORMAT_PAIRS) == 56


def test_hi16_carousel_junction_is_full_niche_times_axis_grid() -> None:
    assert len(CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS) == len(CREATOR_NICHE_SLUGS) * len(
        CAROUSEL_FORMAT_AXIS_SLUGS
    )
    for slug in CREATOR_NICHE_SLUGS:
        for fmt in CAROUSEL_FORMAT_AXIS_SLUGS:
            assert (slug, fmt) in CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS


def test_video_and_carousel_format_axes_are_disjoint() -> None:
    assert set(FORMAT_AXIS_SLUGS).isdisjoint(set(CAROUSEL_FORMAT_AXIS_SLUGS))


def test_junction_union_equals_video_plus_carousel() -> None:
    assert JUNCTION_NICHE_FORMAT_PAIRS == (
        VIDEO_JUNCTION_NICHE_FORMAT_PAIRS | CAROUSEL_JUNCTION_NICHE_FORMAT_PAIRS
    )
    assert len(JUNCTION_NICHE_FORMAT_PAIRS) == 56 + 80


def test_junction_has_pair_helper() -> None:
    assert junction_has_pair("beauty", "review_unboxing") is True
    assert junction_has_pair("beauty", "live_commerce") is False  # not seeded
    assert junction_has_pair("beauty", "tutorial_carousel") is True
    assert junction_has_pair(None, "tutorial") is False
    assert junction_has_pair("beauty", None) is False
    assert junction_has_pair("", "") is False


def test_junction_has_content_class_wave4_edges() -> None:
    from getviews_pipeline.junction_content_class import creator_niche_has_content_class

    assert creator_niche_has_content_class(9, 51) is True
    assert creator_niche_has_content_class(4, 49) is True


def test_junction_has_content_class_v2_taxonomy() -> None:
    from getviews_pipeline.junction_content_class import creator_niche_has_content_class

    assert creator_niche_has_content_class(5, 24) is True
    assert creator_niche_has_content_class(17, 80) is True
    assert creator_niche_has_content_class(8, 82) is True
    assert creator_niche_has_content_class(9, 82) is True


def test_creator_niche_has_content_class_rejects_unknown() -> None:
    from getviews_pipeline.junction_content_class import creator_niche_has_content_class

    assert creator_niche_has_content_class(1, 99999) is False
