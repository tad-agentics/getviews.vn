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


# Reverse map: creator_niches.id → most-representative niche_taxonomy.id.
# Mirror of ``legacyNicheIdForCreatorNiche()`` in
# ``src/lib/profileNiches.ts``. Both files must stay in sync.
_LEGACY_NICHE_FOR_CREATOR_NICHE: dict[int, int] = {
    1:  2,   # Beauty → Skincare
    2:  3,   # Fashion → Thời trang Phụ kiện
    3:  4,   # Food → Ẩm thực & Ăn uống
    4:  13,  # Lifestyle / Storytelling → Hài / Giải trí (closest legacy bucket)
    5:  13,  # Comedy → Hài / Giải trí
    6:  7,   # Family → Mẹ bỉm
    7:  11,  # Education → EduTok VN
    8:  9,   # Tech & Gaming → Công nghệ (representative; Gaming = legacy 17)
    9:  5,   # Business & Finance → Kinh doanh online
    10: 26,  # Wellness → Sức khoẻ / Wellness
    11: 16,  # Travel & Outdoor Sports → Travel (representative; Sports = legacy 21)
    12: 14,  # Auto & Moto → Ô tô / Xe máy
    13: 19,  # Pets & Home → Pets (representative; Home = legacy 20)
    14: 8,   # Gym & Fitness → Gym / Fitness VN
}


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

    Prefers ``creator_niche_id`` (canonical post-PR3) and resolves to the
    representative legacy niche_id; falls back to the legacy
    ``primary_niche`` column for rows that haven't been backfilled yet
    (defensive — PR3 backfilled every populated row).
    """
    if not row:
        return None
    cni = row.get("creator_niche_id")
    if cni is not None:
        legacy = legacy_niche_id_for_creator_niche(cni)
        if legacy is not None:
            return legacy
    pn = row.get("primary_niche")
    if pn is not None:
        try:
            return int(pn)
        except (TypeError, ValueError):
            return None
    return None
