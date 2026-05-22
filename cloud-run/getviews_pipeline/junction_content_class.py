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
    for cc_id, fmt in list(out.items()):
        if fmt == "comedy_observational":
            out[cc_id] = "observational_relatable"
    v2 = root / "supabase/migrations/20260824000000_taxonomy_v2_art_comedy_ai.sql"
    if v2.is_file():
        m3 = re.search(r"INSERT INTO content_classifications[^;]+;", v2.read_text(encoding="utf-8"), re.DOTALL)
        if m3:
            for r in re.findall(
                r"\(\s*(\d+)\s*,\s*'([^']+)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,"
                r"\s*'([^']+)'\s*,\s*'([^']+)'",
                m3.group(0),
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

    # HI-16: carousel grid for active creator niches (excludes retired pets_home 13)
    _ACTIVE_CAROUSEL_NICHE_IDS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17)
    for cn_id in _ACTIVE_CAROUSEL_NICHE_IDS:
        for cc_id in range(75, 80):
            edges.append((cn_id, cc_id, True))

    wave4 = root / "supabase/migrations/20260823000002_wave4_approved_junction_edges.sql"
    if wave4.is_file():
        t4 = wave4.read_text(encoding="utf-8")
        for a, b, p in re.findall(
            r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(TRUE|FALSE)\s*\)",
            t4,
        ):
            edges.append((int(a), int(b), p == "TRUE"))

    edges = _apply_retire_comedy_pets_home(root, edges)
    edges = _apply_taxonomy_feedback_fixes(root, edges)
    edges = _apply_taxonomy_v2_expansion(root, edges)

    return edges


def _apply_taxonomy_v2_expansion(
    root: Path,
    edges: list[tuple[int, int, bool]],
) -> list[tuple[int, int, bool]]:
    """Mirror ``20260824000000_taxonomy_v2_art_comedy_ai.sql`` — comedy restore + art + AI."""
    v2 = root / "supabase/migrations/20260824000000_taxonomy_v2_art_comedy_ai.sql"
    if not v2.is_file():
        return edges
    by_key: dict[tuple[int, int], bool] = {(cn, cc): p for cn, cc, p in edges}
    t = v2.read_text(encoding="utf-8")
    for cc in (24, 25, 26, 27):
        if (4, cc) in by_key:
            by_key[(4, cc)] = False
    for a, b, p in re.findall(
        r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(TRUE|FALSE)\s*\)",
        t,
    ):
        cn, cc = int(a), int(b)
        if cn in (4, 5, 8, 9, 17) and cc not in range(75, 80):
            by_key[(cn, cc)] = p == "TRUE"
    for cn in (5, 17):
        for cc in range(75, 80):
            by_key[(cn, cc)] = True
    return [(cn, cc, p) for (cn, cc), p in by_key.items()]


def _apply_retire_comedy_pets_home(root: Path, edges: list[tuple[int, int, bool]]) -> list[tuple[int, int, bool]]:
    """Mirror ``20260728000000_retire_comedy_pets_home_niches.sql`` junction changes."""
    retire = root / "supabase/migrations/20260728000000_retire_comedy_pets_home_niches.sql"
    if not retire.is_file():
        return edges
    filtered = [(cn, cc, p) for cn, cc, p in edges if cn not in (5, 13)]
    by_key: dict[tuple[int, int], bool] = {(cn, cc): p for cn, cc, p in filtered}
    t = retire.read_text(encoding="utf-8")
    for a, b, p in re.findall(
        r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(TRUE|FALSE)\s*\)",
        t,
    ):
        cn, cc = int(a), int(b)
        if cn == 4:
            by_key[(cn, cc)] = p == "TRUE"
    return [(cn, cc, p) for (cn, cc), p in by_key.items()]


def _apply_taxonomy_feedback_fixes(
    root: Path,
    edges: list[tuple[int, int, bool]],
) -> list[tuple[int, int, bool]]:
    """Promote lifestyle primary for absorbed comedy + pets/home (``20260823000003``)."""
    fix = root / "supabase/migrations/20260823000003_taxonomy_feedback_fixes.sql"
    if not fix.is_file():
        return edges
    promote_ids = {24, 25, 26, 27, 69, 70, 71, 72, 73, 74}
    out: list[tuple[int, int, bool]] = []
    for cn, cc, is_primary in edges:
        if cn == 4 and cc in promote_ids:
            out.append((cn, cc, True))
        else:
            out.append((cn, cc, is_primary))
    return out


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


@lru_cache(maxsize=1)
def _junction_niche_class_pairs() -> frozenset[tuple[int, int]]:
    """All ``(creator_niche_id, content_class_id)`` edges from migration seeds."""
    return frozenset((cn, cc) for cn, cc, _ in _junction_edges())


def creator_niche_has_content_class(creator_niche_id: int, content_class_id: int) -> bool:
    """TD-6 hard gate — ``content_class_id`` must be a junction edge for the niche."""
    if creator_niche_id <= 0 or content_class_id <= 0:
        return False
    return (int(creator_niche_id), int(content_class_id)) in _junction_niche_class_pairs()
