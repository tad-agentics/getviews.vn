"""Phase C — destination dispatch matrix (§A, phase-c-plan.md).

Maps classified intent ids to concrete app destinations. Client mirrors this in
`src/routes/_app/intent-router.ts` as `INTENT_DESTINATIONS`.
"""

from __future__ import annotations

from typing import Literal

from getviews_pipeline.intents import QueryIntent

# String form matches TypeScript `Destination` post-C.7 (no "chat").
Destination = Literal[
    "video",
    "channel",
    "kol",
    "script",
    "answer:pattern",
    "answer:ideas",
    "answer:timing",
    "answer:generic",
]

# Fixed intents → destination. follow_up_classifiable is resolved at runtime via subject.
INTENT_TO_DESTINATION: dict[str, Destination] = {
    # §A.1 — existing screens
    QueryIntent.VIDEO_DIAGNOSIS.value: "video",
    QueryIntent.COMPETITOR_PROFILE.value: "channel",
    QueryIntent.OWN_CHANNEL.value: "channel",
    QueryIntent.FIND_CREATORS.value: "kol",
    "creator_search": "kol",  # SPA alias for find_creators
    QueryIntent.SHOT_LIST.value: "script",
    QueryIntent.METADATA_ONLY.value: "video",
    QueryIntent.SERIES_AUDIT.value: "video",
    # §A.2 — /answer report formats
    QueryIntent.TREND_SPIKE.value: "answer:pattern",
    QueryIntent.CONTENT_DIRECTIONS.value: "answer:pattern",
    QueryIntent.SUBNICHE_BREAKDOWN.value: "answer:pattern",
    QueryIntent.FORMAT_LIFECYCLE_OPTIMIZE.value: "answer:pattern",
    QueryIntent.FATIGUE.value: "answer:pattern",
    QueryIntent.BRIEF_GENERATION.value: "answer:ideas",
    QueryIntent.HOOK_VARIANTS.value: "answer:ideas",
    QueryIntent.TIMING.value: "answer:timing",
    QueryIntent.CONTENT_CALENDAR.value: "answer:pattern",
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
