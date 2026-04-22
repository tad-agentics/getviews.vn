"""Phase C — destination dispatch matrix (§A, phase-c-plan.md).

Maps classified intent ids to concrete app destinations. Client mirrors this in
`src/routes/_app/intent-router.ts` as `INTENT_DESTINATIONS`.
"""

from __future__ import annotations

import re
from typing import Literal

from getviews_pipeline.intents import QueryIntent

# String form matches TypeScript `Destination` post-C.7 (no "chat").
# ``answer:lifecycle`` added 2026-04-22 for the Lifecycle template (serves
# ``format_lifecycle_optimize``, ``fatigue``, ``subniche_breakdown`` —
# previously force-fit into the Pattern template).
Destination = Literal[
    "video",
    "channel",
    "kol",
    "script",
    "answer:pattern",
    "answer:ideas",
    "answer:timing",
    "answer:lifecycle",
    "answer:generic",
]

# Fixed intents → destination. follow_up_classifiable is resolved at runtime via subject.
INTENT_TO_DESTINATION: dict[str, Destination] = {
    # §A.1 — existing screens.
    # 2026-04-22 cleanup: ``series_audit`` + ``comparison`` intents
    # dropped; ``creator_search`` is the canonical creator-discovery
    # label (``find_creators`` kept as a back-compat alias).
    QueryIntent.VIDEO_DIAGNOSIS.value: "video",
    QueryIntent.COMPETITOR_PROFILE.value: "channel",
    QueryIntent.OWN_CHANNEL.value: "channel",
    QueryIntent.CREATOR_SEARCH.value: "kol",
    QueryIntent.FIND_CREATORS.value: "kol",  # legacy alias
    QueryIntent.SHOT_LIST.value: "script",
    QueryIntent.METADATA_ONLY.value: "video",
    QueryIntent.OWN_FLOP_NO_URL.value: "answer:pattern",
    # §A.2 — /answer report formats
    QueryIntent.TREND_SPIKE.value: "answer:pattern",
    QueryIntent.CONTENT_DIRECTIONS.value: "answer:pattern",
    # Lifecycle template (2026-04-22): three intents that were previously
    # rendered as Pattern reports but really need the stage pill + reach
    # delta + health score shape.
    QueryIntent.SUBNICHE_BREAKDOWN.value: "answer:lifecycle",
    QueryIntent.FORMAT_LIFECYCLE_OPTIMIZE.value: "answer:lifecycle",
    QueryIntent.FATIGUE.value: "answer:lifecycle",
    QueryIntent.BRIEF_GENERATION.value: "answer:ideas",
    QueryIntent.HOOK_VARIANTS.value: "answer:ideas",
    QueryIntent.TIMING.value: "answer:timing",
    # ``content_calendar`` merged into timing on 2026-04-22 (Branch 1).
    QueryIntent.CONTENT_CALENDAR.value: "answer:timing",
    # Legacy ``comparison`` reading from historical sessions → fall back
    # to the KOL screen.
    QueryIntent.COMPARISON.value: "kol",
    QueryIntent.FOLLOW_UP_UNCLASSIFIABLE.value: "answer:generic",
}


def destination_for_intent(intent_id: str) -> Destination | None:
    """Return destination for a fixed intent id, or None if unknown / dynamic."""
    return INTENT_TO_DESTINATION.get(intent_id)


def destination_for_follow_up_classifiable(subject: Literal["pattern", "ideas", "timing"]) -> Destination:
    """C.7 `follow_up_classifiable` — classifier supplies subject family."""
    return f"answer:{subject}"  # type: ignore[return-value]


def resolve_destination(intent_id: str, *, follow_up_subject: str | None = None) -> Destination | None:
    """Resolve final destination including dynamic follow-up."""
    if intent_id == QueryIntent.FOLLOW_UP_CLASSIFIABLE.value:
        if follow_up_subject in ("pattern", "ideas", "timing"):
            return destination_for_follow_up_classifiable(follow_up_subject)  # type: ignore[arg-type]
        return None
    return destination_for_intent(intent_id)


# Gemini classifier primary labels → same Destination union as §A (C.0.1 preview field).
# 2026-04-22 cleanup: dropped ``series_audit``; ``find_creators`` kept as
# alias (the classifier no longer emits it but old cached rounds might);
# ``content_calendar`` rerouted to timing (Branch 1).
_GEMINI_PRIMARY_TO_DESTINATION: dict[str, Destination] = {
    "video_diagnosis": "video",
    "content_directions": "answer:pattern",
    "trend_spike": "answer:pattern",
    "brief_generation": "answer:ideas",
    "shot_list": "script",
    "competitor_profile": "channel",
    "own_channel": "channel",
    "creator_search": "kol",
    "find_creators": "kol",  # legacy alias
    "metadata_only": "video",
    "timing": "answer:timing",
    "fatigue": "answer:lifecycle",
    "hook_variants": "answer:ideas",
    "content_calendar": "answer:timing",
    "subniche_breakdown": "answer:lifecycle",
    "format_lifecycle_optimize": "answer:lifecycle",
    # ``comparison`` kept only so legacy session preview rounds still
    # route somewhere sensible; the classifier no longer emits it.
    "comparison": "kol",
    "own_flop_no_url": "answer:pattern",
    "follow_up": "answer:generic",
}


def destination_for_gemini_primary_label(primary: str) -> Destination:
    """Map ``classify_intent_gemini`` / merged ``primary`` string → app destination."""
    return _GEMINI_PRIMARY_TO_DESTINATION.get(primary, "answer:generic")


# ── §A.4 — multi-intent merge detection (C.5.3) ────────────────────────────

# Content-calendar / "post gì khi nào" keyword cues that should add a timing
# subreport to an otherwise Pattern-shaped answer. Matches the plan's
# "Report + timing" merge case (intent #18 content_calendar).
_TIMING_MERGE_RE = re.compile(
    r"(giờ nào|thứ mấy|khi nào post|post khi nào|post .{0,12}khi nào|"
    r"khung giờ|lịch post|thời điểm đăng|post giờ|best time|posting time)",
    re.IGNORECASE,
)


def detect_pattern_subreports(query: str) -> list[str]:
    """Return the list of subreports to fold into a Pattern payload.

    C.5.3 scope: only ``"timing"`` is auto-merged today. The classifier
    (C.7) can supersede this with a richer shape; until then, a keyword
    pass gives us the "Post gì khi nào" merge case without the LLM call.
    """
    q = (query or "").strip()
    if not q:
        return []
    subs: list[str] = []
    if _TIMING_MERGE_RE.search(q):
        subs.append("timing")
    return subs
