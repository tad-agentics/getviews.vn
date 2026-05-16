"""Tests for ``profile_niches.py`` — the BE side of the two-axis
creator_niche → legacy niche_id mapping.

Mirror of the FE helper in ``src/lib/profileNiches.ts``
``legacyNicheIdForCreatorNiche``. Both must stay in sync; these tests
pin the BE side. When updating the mapping, update BOTH this file and
the FE helper.
"""

from __future__ import annotations

import pytest

from getviews_pipeline.profile_niches import (
    creator_niche_id_for_legacy_niche,
    legacy_niche_id_for_creator_niche,
    resolve_legacy_niche_from_profile_row,
)


@pytest.mark.parametrize(
    "creator_niche_id,expected",
    [
        (1,  2),   # Beauty → Skincare
        (2,  3),   # Fashion
        (3,  4),   # Food
        (4,  13),  # Lifestyle / Storytelling → Hài
        (5,  13),  # Comedy → Hài
        (6,  7),   # Family → Mẹ bỉm
        (7,  11),  # Education → EduTok
        (8,  9),   # Tech & Gaming → Tech (representative)
        (9,  5),   # Business & Finance → Kinh doanh
        (10, 26),  # Wellness
        (11, 16),  # Travel & Outdoor Sports → Travel (representative)
        (12, 14),  # Auto & Moto
        (13, 19),  # Pets & Home → Pets (representative)
        (14, 8),   # Gym & Fitness
        (15, 13),  # Music & Dance → Hài / Giải trí
        (16, 10),  # Real Estate → Bất động sản
    ],
)
def test_legacy_niche_id_for_creator_niche(creator_niche_id: int, expected: int) -> None:
    assert legacy_niche_id_for_creator_niche(creator_niche_id) == expected


def test_legacy_niche_id_unknown() -> None:
    assert legacy_niche_id_for_creator_niche(999) is None
    assert legacy_niche_id_for_creator_niche(None) is None


def test_creator_niche_id_for_legacy_niche_tie_break() -> None:
    assert creator_niche_id_for_legacy_niche(26) == 10
    assert creator_niche_id_for_legacy_niche(13) == 4  # lowest among 4,5,15 → 13
    assert creator_niche_id_for_legacy_niche(999) is None
    assert creator_niche_id_for_legacy_niche(None) is None


def test_resolve_uses_creator_niche_id() -> None:
    # PR6 (2026-05-13): primary_niche column dropped; creator_niche_id is
    # the only source. Beauty (1) → representative legacy id 2 (Skincare).
    assert resolve_legacy_niche_from_profile_row({"creator_niche_id": 1}) == 2
    assert resolve_legacy_niche_from_profile_row({"creator_niche_id": 14}) == 8


def test_resolve_returns_none_for_pre_onboarding() -> None:
    assert resolve_legacy_niche_from_profile_row({"creator_niche_id": None}) is None
    assert resolve_legacy_niche_from_profile_row({}) is None
    assert resolve_legacy_niche_from_profile_row(None) is None


def test_resolve_returns_none_for_unknown_creator_niche_id() -> None:
    assert resolve_legacy_niche_from_profile_row({"creator_niche_id": 999}) is None
