"""Profile niche helpers for the two-axis taxonomy refactor (2026-05-10).

Mirrors ``src/lib/profileNiches.ts`` so FE + BE resolve the same
representative legacy ``niche_taxonomy.id`` for a given
``creator_niches.id``. Both must stay in sync; they encode the
"if a creator picked Beauty, what legacy niche does Cloud Run query
video_corpus on" rule.

PR5 of the two-axis refactor: Cloud Run profile reads switch from
``profiles.primary_niche`` to ``profiles.creator_niche_id``. Downstream
code (compute_pulse, pattern thesis, hook_effectiveness lookups) still
filters ``video_corpus.niche_id = X``, so we resolve the legacy id at
the read boundary instead of rewriting every query.
"""

from __future__ import annotations

from typing import Any

# Reverse map: creator_niches.id → most-representative niche_taxonomy.id.
# Mirror of ``legacyNicheIdForCreatorNiche()`` in
# ``src/lib/profileNiches.ts``. Both files must stay in sync.
#
# Keep for ≥30 days after PR6 and until analysis pivots off
# ``video_corpus.niche_id`` / this representative mapping (see
# ``artifacts/docs/two-axis-niche-cutover-runbook.md``).

# Slug → creator_niches.id — mirrors seed; used by HI-11 shadow ingest + Gemini mapping.
CREATOR_NICHE_SLUG_TO_ID: dict[str, int] = {
    "beauty": 1,
    "fashion": 2,
    "food": 3,
    "lifestyle": 4,
    "comedy": 5,
    "family": 6,
    "education": 7,
    "tech_gaming": 8,
    "business": 9,
    "wellness": 10,
    "travel": 11,
    "auto": 12,
    "gym_fitness": 14,
    "music_dance": 15,
    "real_estate": 16,
    "art_craft": 17,
}

# Legacy ingest ids retired into niche 27 (20260728). Keep 13/19/20 for cold DB reads.
_LIFESTYLE_LEGACY_NICHE_IDS: frozenset[int] = frozenset({13, 19, 20, 27})

_LEGACY_NICHE_FOR_CREATOR_NICHE: dict[int, int] = {
    1:  2,   # Beauty → Skincare
    2:  3,   # Fashion → Thời trang Phụ kiện
    3:  4,   # Food → Ẩm thực & Ăn uống
    4:  27,  # Lifestyle → Đời sống · Tâm sự (legacy ingest)
    5:  13,  # Comedy → Hài · Giải trí (restored v2)
    6:  7,   # Family → Mẹ bỉm
    7:  11,  # Education → EduTok VN
    8:  9,   # Tech & Gaming → Công nghệ (representative; Gaming = legacy 17)
    9:  5,   # Business & Finance → Kinh doanh online
    10: 26,  # Wellness → Sức khoẻ / Wellness
    11: 16,  # Travel & Outdoor Sports → Travel (representative; Sports = legacy 21)
    12: 14,  # Auto & Moto → Ô tô / Xe máy
    14: 8,   # Gym & Fitness → Gym / Fitness VN
    15: 28,  # Music & Dance → Âm nhạc · Vũ đạo (legacy ingest)
    16: 10,  # Real Estate → Bất động sản (niche_taxonomy)
    17: 29,  # Art & Craft → Nghệ thuật · Thủ công (v2)
}


def _canonical_legacy_niche_id(legacy_id: int) -> int:
    """Map retired taxonomy ids to surviving ingest bucket (mirror ``profileNiches.ts``)."""
    aliases = {
        19: 27,
        20: 27,
        22: 28,
    }
    return aliases.get(int(legacy_id), int(legacy_id))


def creator_niche_id_for_legacy_niche(legacy_niche_id: int | None) -> int | None:
    """Inverse of ``legacy_niche_id_for_creator_niche`` — pick one creator niche per legacy id.

    When multiple creator niches map to the same legacy representative, returns the
    **lowest** creator_niche_id for a stable tie-break.
    Returns ``None`` when ``legacy_niche_id`` is unknown.
    """
    if legacy_niche_id is None:
        return None
    canonical = _canonical_legacy_niche_id(int(legacy_niche_id))
    matches = [
        cnid for cnid, lid in _LEGACY_NICHE_FOR_CREATOR_NICHE.items()
        if lid == canonical
    ]
    if not matches:
        return None
    return min(matches)


def legacy_niche_id_for_creator_niche(creator_niche_id: int | None) -> int | None:
    """Return the representative ``niche_taxonomy.id`` for a creator_niche.

    Used at the profile-read boundary so downstream Cloud Run queries
    (``video_corpus.niche_id = X``, ``daily_ritual.niche_id = X``,
    ``cross_creator_patterns.niche_id = X``) keep working unchanged
    during the PR5→PR6 transition window.
    """
    if creator_niche_id is None:
        return None
    return _LEGACY_NICHE_FOR_CREATOR_NICHE.get(int(creator_niche_id))


def resolve_legacy_niche_from_profile_row(row: dict | None) -> int | None:
    """Pick the legacy niche_id for a profile row.

    PR6 (2026-05-13) — legacy ``primary_niche`` column was dropped;
    ``creator_niche_id`` is the only profile niche column. Returns
    ``None`` for pre-onboarding profiles.
    """
    if not row:
        return None
    cni = row.get("creator_niche_id")
    if cni is None:
        return None
    return legacy_niche_id_for_creator_niche(cni)


def content_class_ids_for_legacy_niche(client: Any, legacy_niche_id: int | None) -> list[int]:
    """Junction ``content_class_id`` list for a legacy ingest niche (Round B sounds/trends)."""
    cnid = creator_niche_id_for_legacy_niche(legacy_niche_id)
    if cnid is None or client is None:
        return []
    try:
        res = (
            client.table("creator_niche_content_classes")
            .select("content_class_id")
            .eq("creator_niche_id", cnid)
            .execute()
        )
    except Exception:
        return []
    out: list[int] = []
    for row in res.data or []:
        cc = row.get("content_class_id")
        if cc is not None:
            out.append(int(cc))
    return out
