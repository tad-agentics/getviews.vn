"""Canonical TikTok URL detection patterns.

Single source of truth for the BE side. Two callers consumed two slightly
different regexes before L1.5 — ``intents.py`` accepted ``vt.tiktok.com``
short-links but ``report_video.py`` did not, so a vt-link could be
classified as ``video_diagnosis`` and then fail extraction in the report
builder. This module fixes that drift.

Frontend mirror lives at ``src/routes/_app/intent-router.ts`` (different
runtime, can't import); keep both in sync when adding short-link
subdomains. The FE file has a comment pointing at this module.
"""

from __future__ import annotations

import re

# Match TikTok URLs across every short-link domain TikTok publishes:
# - www.tiktok.com / tiktok.com (canonical)
# - vm.tiktok.com / vt.tiktok.com (share-sheet short links — both used)
# - m.tiktok.com (mobile redirect)
# Path uses ``\S+`` so URLs adjacent to punctuation are still captured.
TIKTOK_URL_RE: re.Pattern[str] = re.compile(
    r"https?://(?:(?:www\.)?tiktok\.com|(?:vm|vt|m)\.tiktok\.com)/\S+",
    re.IGNORECASE,
)
