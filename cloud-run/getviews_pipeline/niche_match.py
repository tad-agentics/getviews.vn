"""Free-text niche matcher.

Scans a Vietnamese / mixed-language query for niche mentions by comparing
against niche_taxonomy rows (name_en / name_vn / signal_hashtags). Returns
the canonical niche label instead of the raw first-40-chars fallback that
`helpers.infer_niche_from_hashtags` produces on prose queries like

    "review đồ skincare Hàn Quốc cho da dầu mụn, target khách hàng 18-25"

The whole row set is cached in-process after the first call — niche_taxonomy
is tiny and changes rarely.
"""

from __future__ import annotations

import logging
import re
import threading
import unicodedata
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Words stripped before substring matching. These are Vietnamese connectives /
# verbs / generic content words that never carry niche signal and would cause
# false substring hits (e.g. "review" matching a "reviewer" niche).
_STOPWORDS: frozenset[str] = frozenset({
    "review", "video", "tiktok", "của", "cho", "về", "và", "nhưng", "hay",
    "với", "cùng", "trên", "dưới", "trong", "ngoài", "target", "khách",
    "hàng", "người", "ngách", "lĩnh", "vực", "niche", "content", "làm",
    "nội", "dung",
})

# Cache the taxonomy rows for the lifetime of the process.
_taxonomy_cache: list[dict[str, Any]] | None = None
_taxonomy_lock = threading.Lock()


_D_TRANSLATION = str.maketrans({"đ": "d", "Đ": "D"})


def _strip_accents(s: str) -> str:
    """Fold Vietnamese diacritics so 'làm đẹp' matches 'lam dep' in any of the
    three columns we search — and vice versa when the taxonomy is stored with
    diacritics but the user types without them.

    Unicode NFKD handles combining marks (à → a + ̀) but Vietnamese `đ`/`Đ`
    (U+0111 / U+0110) are standalone letters, not precomposed — they need an
    explicit translation table.
    """
    nfkd = unicodedata.normalize("NFKD", s).translate(_D_TRANSLATION)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(s: str) -> str:
    """Lowercase + strip accents + collapse whitespace for robust substring matching."""
    folded = _strip_accents(s.lower())
    return re.sub(r"\s+", " ", folded).strip()


@dataclass(frozen=True)
class NicheMatch:
    niche_id: int
    name_en: str
    name_vn: str
    matched_on: str   # "hashtag" | "name_vn" | "name_en"
    matched_token: str
    label: str        # preferred Vietnamese label for citations

    def asdict(self) -> dict[str, Any]:
        return {
            "niche_id": self.niche_id,
            "name_en": self.name_en,
            "name_vn": self.name_vn,
            "matched_on": self.matched_on,
            "matched_token": self.matched_token,
            "label": self.label,
        }


def _fetch_taxonomy(client: Any) -> list[dict[str, Any]]:
    global _taxonomy_cache
    with _taxonomy_lock:
        if _taxonomy_cache is not None:
            return _taxonomy_cache
        try:
            r = (
                client.table("niche_taxonomy")
                .select("id, name_en, name_vn, signal_hashtags")
                .execute()
            )
            _taxonomy_cache = r.data or []
        except Exception as exc:
            logger.warning("[niche_match] taxonomy fetch failed: %s", exc)
            _taxonomy_cache = []
        return _taxonomy_cache


def _invalidate_taxonomy_cache() -> None:
    """Clear the in-process taxonomy cache (test hook)."""
    global _taxonomy_cache
    with _taxonomy_lock:
        _taxonomy_cache = None


def find_niche_match(client: Any, query: str) -> NicheMatch | None:
    """Scan `query` for the most specific niche_taxonomy hit.

    Match precedence (most → least specific):
      1. `signal_hashtags` — e.g. `#skincare` appears as a whole token in the query
      2. `name_vn` substring — "làm đẹp" found inside the query
      3. `name_en` substring — "skincare" found inside the query

    Single-word tokens from the query are also checked against the taxonomy
    row's name fields (handles the case where the user writes "skincare" but
    the taxonomy stores "Skincare & làm đẹp").

    Stopwords in _STOPWORDS are ignored to avoid false hits like "review"
    matching a "review đồ" niche when the query is talking about something else.
    """
    q = (query or "").strip()
    if not q:
        return None

    rows = _fetch_taxonomy(client)
    if not rows:
        return None

    qn = _normalize(q)
    tokens = [t for t in re.findall(r"[\w#]+", qn) if t and t not in _STOPWORDS]
    token_set = set(tokens)

    # 1. signal_hashtags — requires exact token match (bare or with #).
    for row in rows:
        tags = row.get("signal_hashtags") or []
        for tag in tags:
            t = _normalize(str(tag)).lstrip("#")
            if not t or t in _STOPWORDS:
                continue
            if t in token_set or f"#{t}" in token_set:
                return NicheMatch(
                    niche_id=int(row["id"]),
                    name_en=row.get("name_en") or "",
                    name_vn=row.get("name_vn") or "",
                    matched_on="hashtag",
                    matched_token=t,
                    label=row.get("name_vn") or row.get("name_en") or t,
                )

    # 2. name_vn substring.
    for row in rows:
        nv = _normalize(row.get("name_vn") or "")
        if nv and nv not in _STOPWORDS and nv in qn:
            return NicheMatch(
                niche_id=int(row["id"]),
                name_en=row.get("name_en") or "",
                name_vn=row.get("name_vn") or "",
                matched_on="name_vn",
                matched_token=nv,
                label=row.get("name_vn") or row.get("name_en") or nv,
            )

    # 3. name_en substring.
    for row in rows:
        ne = _normalize(row.get("name_en") or "")
        if ne and ne not in _STOPWORDS and ne in qn:
            return NicheMatch(
                niche_id=int(row["id"]),
                name_en=row.get("name_en") or "",
                name_vn=row.get("name_vn") or "",
                matched_on="name_en",
                matched_token=ne,
                label=row.get("name_vn") or row.get("name_en") or ne,
            )

    return None
