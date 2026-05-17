"""§11 curated creator slang — tiers + deterministic merge into extraction JSON.

Gemini fills ``slang_terms_used`` / ``slang_freshness_score``; this module adds
lexicon hits from ``audio_transcript`` + ``text_overlays`` so seeded slang is
not missed. Quarterly curation: extend ``SLANG_LEXICON``.
"""

from __future__ import annotations

from typing import Literal

Freshness = Literal["current_quarter", "last_quarter", "dated"]

# Lowercase-normalized matching uses these canonical display strings as returned terms.
SLANG_LEXICON: dict[str, Freshness] = {
    "+1 máy": "current_quarter",
    "đỉnh khoai": "current_quarter",
    "toang": "last_quarter",
    "bớt ảo tưởng đi má": "dated",
    "xịn xò": "last_quarter",
    "gánh team": "last_quarter",
}

_FRESHNESS_RANK: dict[str, int] = {
    "current_quarter": 2,
    "last_quarter": 1,
    "dated": 0,
}


def _norm(s: str) -> str:
    return str(s or "").strip().lower()


def find_slang_terms_in_text(text: str) -> list[str]:
    if not str(text or "").strip():
        return []
    hay = str(text).lower()
    found: list[str] = []
    seen: set[str] = set()
    for phrase in sorted(SLANG_LEXICON, key=len, reverse=True):
        pl = phrase.lower()
        if pl and pl in hay:
            key = phrase.strip()
            lk = key.lower()
            if lk not in seen:
                seen.add(lk)
                found.append(key)
    return found


def _tier_for_phrase(phrase: str) -> Freshness | None:
    return SLANG_LEXICON.get(phrase.strip())


def pick_worse_freshness(a: str | None, b: str | None) -> str | None:
    """Return the more stale of two tier labels (dated wins over current_quarter)."""

    def norm_tier(x: str | None) -> str | None:
        if not x:
            return None
        s = str(x).strip().lower().replace("-", "_")
        return s if s in _FRESHNESS_RANK else None

    na, nb = norm_tier(a), norm_tier(b)
    if na is None:
        return nb
    if nb is None:
        return na
    return na if _FRESHNESS_RANK[na] <= _FRESHNESS_RANK[nb] else nb


def merge_lexicon_slang_into_video_analysis_dict(d: dict) -> None:
    """Mutate analysis dict in place before/after Pydantic validation."""
    if not isinstance(d, dict):
        return
    chunks: list[str] = [str(d.get("audio_transcript") or "")]
    for o in d.get("text_overlays") or []:
        if isinstance(o, dict) and o.get("text"):
            chunks.append(str(o["text"]))
    hay = "\n".join(chunks)
    lex_hits = find_slang_terms_in_text(hay)
    cur = [
        str(x).strip() for x in (d.get("slang_terms_used") or []) if str(x).strip()
    ]
    seen = {x.lower() for x in cur}
    for h in lex_hits:
        if h.lower() not in seen:
            cur.append(h)
            seen.add(h.lower())
    if cur:
        d["slang_terms_used"] = cur

    tiers: list[str] = []
    for term in cur:
        tl = _tier_for_phrase(term)
        if tl:
            tiers.append(tl)
        else:
            for phrase, tier in SLANG_LEXICON.items():
                if _norm(phrase) in _norm(term) or _norm(term) in _norm(phrase):
                    tiers.append(tier)
                    break
    if not tiers:
        return
    worst = min(tiers, key=lambda x: _FRESHNESS_RANK.get(x, 99))
    d["slang_freshness_score"] = pick_worse_freshness(
        d.get("slang_freshness_score") if isinstance(d.get("slang_freshness_score"), str) else None,
        worst,
    )
