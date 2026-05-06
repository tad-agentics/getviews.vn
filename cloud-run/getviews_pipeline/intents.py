"""Intent enum + URL/handle/question parsing helpers.

The deterministic intent classifier (``classify_intent``) and its
companions (``merge_deterministic_with_gemini``,
``query_intent_to_gemini_primary``) were removed L1.5 audit. The
report-based UX classifies client-side via ``intent-router.ts``;
``/stream``'s null-intent fallback uses ``classify_intent_gemini``
(Gemini-backed) directly. This module is now scoped to: the
``QueryIntent`` enum (kept as the FE-mirror contract + ``pipelines.py``
session tracking), the TikTok URL regex (canonical version lives in
``url_patterns``), and free-text question splitting used by ``/stream``.
"""

from __future__ import annotations

import re
from enum import StrEnum

from getviews_pipeline.url_patterns import TIKTOK_URL_RE


class QueryIntent(StrEnum):
    """Intent taxonomy — mirror of ``GEMINI_CLASSIFIER_PRIMARY_LABELS``.

    Historical removals:
      - ``SERIES_AUDIT`` removed 2026-04-22 (no template, not classified).
      - ``COMPARISON`` removed L1.5 (Tier B). Was a deprecated alias for
        ``COMPETITOR_PROFILE`` kept only for historical session reads —
        ``routers/intent.py:_normalize_intent_name`` now folds the legacy
        ``"comparison"`` string into ``competitor_profile`` at the router
        edge so any historical-session intent_type still resolves.
      - ``FIND_CREATORS`` removed L1.5 (Tier B). Was a deprecated alias
        for ``CREATOR_SEARCH``; same back-compat normaliser strategy.
      - ``FOLLOWUP`` removed L1.5 (Tier B). Chat-era catch-all replaced
        by ``FOLLOW_UP_CLASSIFIABLE`` / ``FOLLOW_UP_UNCLASSIFIABLE``.
        Legacy ``"followup"`` strings normalised to ``"follow_up"``.
      - ``METADATA_ONLY`` removed L1.5 (audit). Pre-template-migration this
        routed to a dedicated /app/video corpus-row preview that skipped
        Gemini; post-migration it falls through to ``build_generic_report``
        which DOES call Gemini. The "no-cost stats preview" promise was
        broken silently, so the intent provided zero UX differentiation
        vs FOLLOW_UP_UNCLASSIFIABLE. Legacy strings normalised at the
        router edge to ``follow_up_unclassifiable``.
    """

    VIDEO_DIAGNOSIS = "video_diagnosis"
    CONTENT_DIRECTIONS = "content_directions"
    COMPETITOR_PROFILE = "competitor_profile"
    BRIEF_GENERATION = "brief_generation"
    TREND_SPIKE = "trend_spike"
    OWN_CHANNEL = "own_channel"  # "Soi Kênh" — same pipeline as video_diagnosis
    CREATOR_SEARCH = "creator_search"  # canonical label for KOL/creator discovery
    SHOT_LIST = "shot_list"  # detailed shot list for production
    # Phase C §A.2 — ``/answer`` report intents (Gemini-classified).
    SUBNICHE_BREAKDOWN = "subniche_breakdown"
    FORMAT_LIFECYCLE_OPTIMIZE = "format_lifecycle_optimize"
    FATIGUE = "fatigue"
    HOOK_VARIANTS = "hook_variants"
    TIMING = "timing"
    CONTENT_CALENDAR = "content_calendar"
    # Wave 4 PR #1 (2026-05-11) — two-URL side-by-side diagnosis. Distinct
    # from the retired ``COMPARISON`` (handle-based) + retired
    # ``SERIES_AUDIT`` (multi-URL corpus) intents; this one ships a real
    # template. See artifacts/docs/implementation-plan.md Wave 4.
    COMPARE_VIDEOS = "compare_videos"
    OWN_FLOP_NO_URL = "own_flop_no_url"  # own channel/video underperforming, no TikTok URL
    FOLLOW_UP_CLASSIFIABLE = "follow_up_classifiable"
    FOLLOW_UP_UNCLASSIFIABLE = "follow_up_unclassifiable"


# L1.5 — canonical pattern moved to url_patterns module so report_video.py
# uses the same definition (was missing vt.tiktok.com short-links before).
_TIKTOK_URL_RE = TIKTOK_URL_RE
_HANDLE_RE = re.compile(r"@([a-zA-Z0-9_.]+)")


def _strip_urls(text: str) -> str:
    """Remove all TikTok URL spans before handle extraction so that @username
    embedded in a URL (e.g. tiktok.com/@foo/video/123) is not treated as a
    standalone @handle mention."""
    return _TIKTOK_URL_RE.sub("", text)


def extract_urls_and_handles(message: str) -> tuple[list[str], list[str]]:
    urls = _TIKTOK_URL_RE.findall(message)
    handles = _HANDLE_RE.findall(_strip_urls(message))
    return urls, handles


def split_into_questions(message: str) -> list[str]:
    """Split multi-part user messages on common English and Vietnamese conjunctions."""
    raw = message.strip()
    if not raw:
        return []
    # Splits on: "Also," / "Ngoài ra" / "Và " (sentence-starting "And") /
    # "Thêm nữa" / "Bên cạnh đó" / double newline
    parts = re.split(
        r"\bAlso,|(?<=[.!?])\s+Và\s+|Ngoài ra[,\s]|Thêm nữa[,\s]|Bên cạnh đó[,\s]|\n\n+",
        raw,
        flags=re.IGNORECASE,
    )
    out = [p.strip() for p in parts if p.strip()]
    return out if out else [raw]
