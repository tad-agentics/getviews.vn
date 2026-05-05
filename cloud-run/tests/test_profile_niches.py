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
    ],
)
def test_legacy_niche_id_for_creator_niche(creator_niche_id: int, expected: int) -> None:
    assert legacy_niche_id_for_creator_niche(creator_niche_id) == expected


def test_legacy_niche_id_unknown() -> None:
    assert legacy_niche_id_for_creator_niche(999) is None
    assert legacy_niche_id_for_creator_niche(None) is None


def test_resolve_prefers_creator_niche_id_over_primary() -> None:
    # creator_niche_id=1 (Beauty) → resolves to legacy 2 (Skincare),
    # NOT the legacy primary_niche=99 (which would be a stale value).
    row = {"creator_niche_id": 1, "primary_niche": 99}
    assert resolve_legacy_niche_from_profile_row(row) == 2


def test_resolve_falls_back_to_primary_when_creator_unset() -> None:
    row = {"creator_niche_id": None, "primary_niche": 4}
    assert resolve_legacy_niche_from_profile_row(row) == 4


def test_resolve_returns_none_for_pre_onboarding() -> None:
    assert resolve_legacy_niche_from_profile_row({"creator_niche_id": None, "primary_niche": None}) is None
    assert resolve_legacy_niche_from_profile_row({}) is None
    assert resolve_legacy_niche_from_profile_row(None) is None


def test_resolve_handles_unknown_creator_niche_id_gracefully() -> None:
    # Unknown creator_niche_id → falls through to primary_niche if set.
    row = {"creator_niche_id": 999, "primary_niche": 4}
    assert resolve_legacy_niche_from_profile_row(row) == 4
    # Unknown + no fallback → None.
    assert resolve_legacy_niche_from_profile_row({"creator_niche_id": 999}) is None


def test_resolve_coerces_string_primary_niche() -> None:
    # primary_niche came back as "4" from a stringified column.
    row = {"creator_niche_id": None, "primary_niche": "4"}
    assert resolve_legacy_niche_from_profile_row(row) == 4
