"""CI guard: no code may query columns that were dropped from ``video_corpus``.

Phase C (migration ``20260822000001_phase_c_drop_video_corpus_niche_id.sql``)
dropped ``video_corpus.niche_id``. PostgREST validates the column list before
matching rows, so any leftover ``.select("...niche_id...")`` or
``.eq("niche_id", ...)`` on ``video_corpus`` raises ``42703`` at runtime —
which is how the corpus fast-path of single-video diagnosis silently broke.

These tests are mocked elsewhere and never touch a live schema, so that drift
went undetected. This static scan locks it in: when a column is dropped from
``video_corpus``, add it to ``DROPPED_VIDEO_CORPUS_COLUMNS`` and migrate every
caller to the surviving surrogate (``ingest_loop_niche_id`` for the legacy
niche, or ``content_class_id`` for the canonical cohort). The PostgREST alias
form ``niche_id:ingest_loop_niche_id`` is allowed — it selects the *surviving*
column under the old key, so readers stay unchanged.
"""

from __future__ import annotations

import re
from pathlib import Path

# Columns removed from video_corpus. Grow this set whenever a column is dropped.
DROPPED_VIDEO_CORPUS_COLUMNS = {"niche_id"}

_ROOT = Path(__file__).parent.parent
_SCAN_DIRS = [_ROOT / "getviews_pipeline", _ROOT / "scripts"]

_TABLE_RE = re.compile(r'(?:\.table|\.from_)\(\s*"video_corpus"\s*\)')
_STRING_RE = re.compile(r'"([^"]*)"')
_EXECUTE_RE = re.compile(r'\.execute\(\)')
_BLOCK_MAX_LINES = 40  # cap so an unterminated block can't swallow the file


def _video_corpus_blocks(text: str) -> list[tuple[int, str]]:
    """Yield (start_line, block_text) for each ``table("video_corpus")`` query.

    A block runs from the ``table(...)`` call through the first ``.execute()``
    (covers incrementally-built ``q = q.eq(...)`` chains), capped for safety.
    """
    lines = text.splitlines()
    blocks: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        if _TABLE_RE.search(lines[i]):
            end = min(i + _BLOCK_MAX_LINES, len(lines))
            j = i
            while j < end:
                if _EXECUTE_RE.search(lines[j]):
                    break
                j += 1
            blocks.append((i + 1, "\n".join(lines[i : j + 1])))
            i = j + 1
        else:
            i += 1
    return blocks


def _real_columns(block: str) -> set[str]:
    """Real column names referenced in a query block.

    Splits every quoted literal on commas and resolves the PostgREST alias
    form ``alias:column`` to its real (right-hand) column, so an alias *to* a
    surviving column does not count as a reference to the dropped name.
    """
    cols: set[str] = set()
    for literal in _STRING_RE.findall(block):
        for spec in literal.split(","):
            spec = spec.strip()
            if ":" in spec:  # PostgREST alias → real column is the RHS
                spec = spec.split(":")[-1].strip()
            if spec:
                cols.add(spec)
    return cols


def test_no_dropped_columns_referenced_on_video_corpus() -> None:
    violations: list[str] = []
    for scan_dir in _SCAN_DIRS:
        for path in sorted(scan_dir.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "video_corpus" not in text:
                continue
            for start_line, block in _video_corpus_blocks(text):
                hit = _real_columns(block) & DROPPED_VIDEO_CORPUS_COLUMNS
                for col in sorted(hit):
                    rel = path.relative_to(_ROOT)
                    violations.append(f"{rel}:{start_line} queries dropped column '{col}'")

    assert not violations, (
        "video_corpus query references a dropped column (PostgREST 42703 at runtime). "
        "Use ingest_loop_niche_id (legacy niche) or content_class_id, or the alias form "
        "niche_id:ingest_loop_niche_id:\n  " + "\n  ".join(violations)
    )
