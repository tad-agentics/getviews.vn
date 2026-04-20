"""Phase C.5.1 — Generic report helpers.

Generic is the humility fallback — no credit charge, bounded narrative,
three off-taxonomy routing chips, three evidence tiles pulled from the
broad corpus.

Length cap (plan §C.5 data model, picked up from tier-1 fix):
- ``narrative.paragraphs[]`` max 2 entries, each ≤ 320 chars.
- Truncation happens at the last sentence boundary before the cap and
  is logged ``[generic-truncated]`` so we can catch Gemini drift early.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


NARRATIVE_PARAGRAPH_MAX_CHARS = 320
NARRATIVE_MAX_PARAGRAPHS = 2

# Static off-taxonomy suggestions — three chips that always render on the
# OffTaxonomyBanner. Order is deliberate: Soi Kênh first (highest-traffic
# fallback), then Xưởng Viết, then Tìm KOL.
OFF_TAXONOMY_SUGGESTIONS: list[dict[str, str]] = [
    {"label": "Soi Kênh", "route": "/app/channel", "icon": "eye"},
    {"label": "Xưởng Viết", "route": "/app/script", "icon": "film"},
    {"label": "Tìm KOL", "route": "/app/kol", "icon": "users"},
]


_SENTENCE_BOUNDARY_RE = re.compile(r"([\.!?…])\s+")


def _truncate_at_sentence(text: str, limit: int) -> str:
    """Return at most ``limit`` characters, ending on a sentence boundary
    when possible. Over-cap input is logged ``[generic-truncated]``.
    """
    t = (text or "").strip()
    if len(t) <= limit:
        return t
    head = t[:limit]
    matches = list(_SENTENCE_BOUNDARY_RE.finditer(head))
    if matches:
        last = matches[-1]
        truncated = head[: last.end()].rstrip()
    else:
        # No sentence boundary in range — fall back to the last word break.
        last_space = head.rfind(" ")
        truncated = head[:last_space].rstrip() + "…" if last_space > 0 else head.rstrip()
    logger.info("[generic-truncated] %d → %d chars", len(t), len(truncated))
    return truncated


def cap_paragraphs(paragraphs: list[str]) -> list[str]:
    """Enforce the §J contract on ``narrative.paragraphs`` — at most 2
    entries, each ≤ 320 chars ending on a sentence boundary where
    possible. Empty strings are filtered out.
    """
    clean = [p.strip() for p in (paragraphs or []) if isinstance(p, str) and p.strip()]
    capped = [
        _truncate_at_sentence(p, NARRATIVE_PARAGRAPH_MAX_CHARS)
        for p in clean[:NARRATIVE_MAX_PARAGRAPHS]
    ]
    return [p for p in capped if p]


def build_off_taxonomy_payload() -> dict[str, Any]:
    """Static suggestions — the three routes users should try instead of
    asking an unclassifiable question."""
    return {"suggestions": [dict(s) for s in OFF_TAXONOMY_SUGGESTIONS]}


# Evidence tile colors — reuse the Pattern palette so Generic + Pattern
# + Ideas render consistent thumbnails when EvidenceCard falls back to
# the server-seeded color.
_TILE_COLORS = ("#D9EB9A", "#E8E4DC", "#C5F0E8", "#F5E6C8", "#1F2A3B", "#2A2438")


def _tile_color_for(idx: int) -> str:
    return _TILE_COLORS[idx % len(_TILE_COLORS)]


def pick_broad_evidence(
    corpus_rows: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Top-``limit`` videos across the broad corpus slice, views desc, one
    per creator. Generic's evidence is intentionally coarse — the user
    asked something unclassifiable, so we surface broadly-watched winners
    rather than narrowly-ranked hooks.
    """
    rows = sorted(
        (r for r in corpus_rows if int(r.get("views") or 0) > 0),
        key=lambda r: int(r.get("views") or 0),
        reverse=True,
    )
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        creator = str(row.get("creator_handle") or "").strip() or "@unknown"
        if creator in seen:
            continue
        seen.add(creator)
        out.append(row)
        if len(out) >= limit:
            break
    return out
