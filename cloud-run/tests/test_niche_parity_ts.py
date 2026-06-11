"""Cross-runtime niche-map parity guard (audit 2026-06-10 hardening).

CLAUDE.md demands ``legacy_niche_id_for_creator_niche`` (Python) and
``legacyNicheIdForCreatorNiche`` (TypeScript) stay identical, and the same
for the retired-id alias maps — but until now that contract was enforced by
"remember to edit both files". These tests parse the TS source so a
one-sided edit fails CI instead of shipping a silent FE/BE divergence.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from getviews_pipeline.profile_niches import (
    _LEGACY_NICHE_FOR_CREATOR_NICHE,
    _canonical_legacy_niche_id,
)

_TS_PATH = Path(__file__).resolve().parents[2] / "src" / "lib" / "profileNiches.ts"

pytestmark = pytest.mark.skipif(
    not _TS_PATH.exists(),
    reason="frontend source not present (standalone cloud-run checkout)",
)


def _ts_source() -> str:
    return _TS_PATH.read_text(encoding="utf-8")


def _parse_ts_switch_map(src: str, fn_name: str) -> dict[int, int]:
    """Extract ``case N: return M;`` pairs from a TS switch-based mapper."""
    fn_match = re.search(
        rf"function {fn_name}\([^)]*\)[^{{]*\{{(.*?)\n\}}", src, re.DOTALL
    )
    assert fn_match, f"{fn_name} not found in {_TS_PATH}"
    body = fn_match.group(1)
    pairs = re.findall(r"case\s+(\d+)\s*:\s*return\s+(\d+)\s*;", body)
    assert pairs, f"no case/return pairs parsed from {fn_name} — TS shape changed?"
    return {int(k): int(v) for k, v in pairs}


def _parse_ts_object_map(src: str, const_name: str) -> dict[int, int]:
    """Extract ``N: M,`` pairs from a TS object-literal const."""
    obj_match = re.search(rf"const {const_name}[^=]*=\s*\{{(.*?)\}};", src, re.DOTALL)
    assert obj_match, f"{const_name} not found in {_TS_PATH}"
    body = obj_match.group(1)
    pairs = re.findall(r"^\s*(\d+)\s*:\s*(\d+)\s*,", body, re.MULTILINE)
    assert pairs, f"no entries parsed from {const_name} — TS shape changed?"
    return {int(k): int(v) for k, v in pairs}


def test_legacy_niche_map_matches_typescript() -> None:
    ts_map = _parse_ts_switch_map(_ts_source(), "legacyNicheIdForCreatorNiche")
    assert ts_map == _LEGACY_NICHE_FOR_CREATOR_NICHE, (
        "legacyNicheIdForCreatorNiche (src/lib/profileNiches.ts) and "
        "_LEGACY_NICHE_FOR_CREATOR_NICHE (profile_niches.py) have diverged — "
        "update BOTH files in the same commit."
    )


def test_retired_alias_map_matches_typescript() -> None:
    ts_aliases = _parse_ts_object_map(_ts_source(), "NICHE_TAXONOMY_ALIASES")
    # Python keeps the aliases inside _canonical_legacy_niche_id; recover the
    # mapping behaviourally over a generous id range.
    py_aliases = {
        i: _canonical_legacy_niche_id(i)
        for i in range(1, 64)
        if _canonical_legacy_niche_id(i) != i
    }
    assert ts_aliases == py_aliases, (
        "NICHE_TAXONOMY_ALIASES (src/lib/profileNiches.ts) and the alias dict in "
        "_canonical_legacy_niche_id (profile_niches.py) have diverged — "
        "update BOTH files in the same commit."
    )
