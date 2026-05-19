"""Derive ``content_class_id`` from (creator_niche_id × format_axis) via PR1/PR6/HI-16 seeds.

HI-11 ``NICHE_RESOLVER_MODE=route`` writes junction-derived IDs instead of the
legacy ``_content_class_for`` ladder when Gemini two-axis classification wins.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_PR1_MIGRATION = "supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql"


def _repo_root() -> Path:
    """Repo root locally (``getviews.vn/``); ``/app`` in Cloud Run when migrations are copied."""
    here = Path(__file__).resolve()
    for base in (here.parents[1], here.parents[2]):
        if (base / _PR1_MIGRATION).is_file():
            return base
    raise FileNotFoundError(
        f"Missing {_PR1_MIGRATION} — Cloud Run image must COPY supabase migrations; "
        "see cloud-run/Dockerfile"
    )


@lru_cache(maxsize=1)
def _content_class_id_to_format_axis() -> dict[int, str]:
    """Parse ``content_classifications`` INSERTs from PR1 + HI-16 migrations."""
    root = _repo_root()
    out: dict[int, str] = {}

    pr1 = (root / "supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql").read_text(
        encoding="utf-8",
    )
    m = re.search(r"INSERT INTO content_classifications[^;]+;", pr1, re.DOTALL)
    assert m is not None
    rows = re.findall(
        r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,"
        r"\s*'([^']+)'\s*,\s*'([^']+)'",
        m.group(0),
    )
    for r in rows:
        out[int(r[0])] = r[4]

    hi16 = root / "supabase/migrations/20260516190000_hi16_carousel_format_axis_junction.sql"
    if hi16.is_file():
        t = hi16.read_text(encoding="utf-8")
        m2 = re.search(r"INSERT INTO content_classifications[^;]+;", t, re.DOTALL)
        if m2:
            for r in re.findall(
                r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,"
                r"\s*'([^']+)'\s*,\s*'([^']+)'",
                m2.group(0),
            ):
                out[int(r[0])] = r[4]
    return out


@lru_cache(maxsize=1)
def _junction_edges() -> list[tuple[int, int, bool]]:
    """All ``(creator_niche_id, content_class_id, is_primary)`` from PR1 + PR6 + HI-16."""
    root = _repo_root()
    edges: list[tuple[int, int, bool]] = []

    pr1 = (root / "supabase/migrations/20260510000004_two_axis_niche_pr1_schema.sql").read_text(
        encoding="utf-8",
    )
    jstart = pr1.find(
        "INSERT INTO creator_niche_content_classes "
        "(creator_niche_id, content_class_id, is_primary) VALUES",
    )
    assert jstart != -1
    jchunk = pr1[jstart : jstart + 12000]
    for a, b, p in re.findall(
        r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(TRUE|FALSE)\s*\)",
        jchunk,
    ):
        edges.append((int(a), int(b), p == "TRUE"))

    pr6 = root / "supabase/migrations/20260630000003_creator_niches_16_music_real_estate.sql"
    if pr6.is_file():
        t6 = pr6.read_text(encoding="utf-8")
        for a, b, p in re.findall(
            r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(TRUE|FALSE)\s*\)",
            t6,
        ):
            edges.append((int(a), int(b), p == "TRUE"))

    # HI-16: CROSS JOIN creator_niches × content_classifications 75–79
    for cn_id in range(1, 17):
        for cc_id in range(75, 80):
            edges.append((cn_id, cc_id, True))

    return edges


@lru_cache(maxsize=1)
def primary_content_class_id_by_niche_and_format() -> dict[tuple[int, str], int]:
    """Map (creator_niche.id, format_axis) → one content_classifications.id.

    When several junction rows share the same format_axis under one niche (e.g.
    Beauty has two ``tutorial`` rows), prefer ``is_primary`` links, then lowest
    ``content_class_id`` for a stable tie-break.
    """
    cc_fmt = _content_class_id_to_format_axis()
    buckets: dict[tuple[int, str], list[tuple[int, bool]]] = {}
    for cn_id, cc_id, is_primary in _junction_edges():
        fmt = cc_fmt.get(cc_id)
        if not fmt:
            continue
        buckets.setdefault((cn_id, fmt), []).append((cc_id, is_primary))

    out: dict[tuple[int, str], int] = {}
    for key, pairs in buckets.items():
        primaries = [cc for cc, p in pairs if p]
        pool = primaries if primaries else [cc for cc, _ in pairs]
        out[key] = min(pool)
    return out


def content_class_id_for_creator_niche_format(
    creator_niche_id: int,
    format_axis: str,
) -> int | None:
    """Return seeded ``content_class_id`` or ``None`` if axis unknown for niche."""
    fmt = (format_axis or "").strip()
    if not fmt:
        return None
    return primary_content_class_id_by_niche_and_format().get((int(creator_niche_id), fmt))
