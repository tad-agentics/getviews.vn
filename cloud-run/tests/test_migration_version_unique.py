"""Migration version-collision tripwire.

Supabase records ONE schema_migrations row per version prefix — when two
local files share a version, one is silently never applied. This exact
failure created the 7-week corpus_ingest_queue outage (P-1, 2026-06-10:
20260721000000 was recorded for gemini_calls_cached_content_tokens and the
queue table never existed), and duplicate versions reappeared twice on
2026-06-10/11. This test makes the collision a CI failure instead of a
production mystery.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"

pytestmark = pytest.mark.skipif(
    not _MIGRATIONS_DIR.exists(),
    reason="migrations dir not present (standalone cloud-run checkout)",
)


def test_migration_versions_are_unique() -> None:
    versions = Counter()
    for f in _MIGRATIONS_DIR.glob("*.sql"):
        m = re.match(r"^(\d{14})_", f.name)
        if m:
            versions[m.group(1)] += 1
    dupes = {v: n for v, n in versions.items() if n > 1}
    assert not dupes, (
        f"Duplicate migration version prefixes {sorted(dupes)} — Supabase "
        "applies only ONE file per version; rename the newer file to a "
        "unique timestamp (this is how the 7-week corpus_ingest_queue "
        "outage happened)."
    )
