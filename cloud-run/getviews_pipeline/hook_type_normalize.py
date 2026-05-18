"""Shared hook_type normalization (TikTok corpus, Douyin corpus, douyin_match).

Keeps ``video_corpus.hook_type`` and ``douyin_video_corpus.hook_type`` aligned with
the ``HookType`` literal in ``models.py`` so §8 peer queries don't miss on aliases
(``tutorial`` → ``how_to``, etc.).
"""

from __future__ import annotations

from typing import get_args

from getviews_pipeline.models import HookType

_HOOK_TYPE_ALIASES: dict[str, str] = {
    # Canonical values — pass through
    "question": "question",
    "bold_claim": "bold_claim",
    "shock_stat": "shock_stat",
    "story_open": "story_open",
    "controversy": "controversy",
    "challenge": "challenge",
    "how_to": "how_to",
    "social_proof": "social_proof",
    "curiosity_gap": "curiosity_gap",
    "pain_point": "pain_point",
    "trend_hijack": "trend_hijack",
    "none": "none",
    "other": "other",
    "warning": "warning",
    "reaction": "reaction",
    "comparison": "comparison",
    "expose": "expose",
    "insider": "insider",
    "secret": "secret",
    "pov": "pov",
    "vach_tran": "vach_tran",
    "gia_soc": "gia_soc",
    "dialect_identity": "dialect_identity",
    "fomo_urgency": "fomo_urgency",
    "tips_value": "tips_value",
    "price_shock": "gia_soc",
    # Vietnamese-language aliases (knowledge_base / Gemini)
    "canh_bao": "warning",
    "phan_ung": "reaction",
    "so_sanh": "comparison",
    "boc_phot": "expose",
    "huong_dan": "how_to",
    "ke_chuyen": "story_open",
    "bang_chung": "social_proof",
    # English synonyms Gemini might use
    "tutorial": "how_to",
    "story": "story_open",
    "storytelling": "story_open",
    "story_telling": "story_open",
    "shock": "bold_claim",
    "tips": "tips_value",
    "fear": "fomo_urgency",
    "curiosity": "curiosity_gap",
}

_HOOK_TYPE_CANONICAL = frozenset(get_args(HookType))


def normalize_hook_type(raw: str | None) -> str:
    s = str(raw or "").strip().lower().replace("-", "_")
    if not s:
        return "other"
    mapped = _HOOK_TYPE_ALIASES.get(s, s)
    if mapped in _HOOK_TYPE_CANONICAL:
        return mapped
    return "other"
