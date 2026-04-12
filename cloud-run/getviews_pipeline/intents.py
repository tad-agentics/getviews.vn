"""§3 intent classification, §3a hybrid detection, collapse, and chain dependencies."""

from __future__ import annotations

import re
from enum import StrEnum


class QueryIntent(StrEnum):
    VIDEO_DIAGNOSIS = "video_diagnosis"
    CONTENT_DIRECTIONS = "content_directions"
    COMPETITOR_PROFILE = "competitor_profile"
    SERIES_AUDIT = "series_audit"
    BRIEF_GENERATION = "brief_generation"
    TREND_SPIKE = "trend_spike"
    METADATA_ONLY = "metadata_only"
    FOLLOWUP = "followup"
    OWN_CHANNEL = "own_channel"  # "Soi Kênh" — same pipeline as video_diagnosis
    FIND_CREATORS = "find_creators"  # KOL/creator search
    SHOT_LIST = "shot_list"  # detailed shot list for production


KNOWLEDGE_SIGNALS = [
    "algorithm",
    "how does tiktok",
    "does the algorithm",
    "shadowban",
    "does tiktok punish",
    "is it still worth",
    "does posting more",
    "seo",
    "keyword",
    "caption",
    "hashtag strategy",
    "new google",
    "keyword stuff",
    "caption keywords",
    "voiceover vs caption",
    "rage bait",
    "deliberate mistake",
    "engagement bait",
    "comment bait",
    "cheat code",
    "hack the algorithm",
    "ring light",
    "mic",
    "gear",
    "lighting setup",
    "lo-fi vs",
    "production quality",
    "phone vs camera",
]

_TIKTOK_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com)/\S+",
    re.IGNORECASE,
)
_HANDLE_RE = re.compile(r"@([a-zA-Z0-9_.]+)")


def extract_urls_and_handles(message: str) -> tuple[list[str], list[str]]:
    urls = _TIKTOK_URL_RE.findall(message)
    handles = _HANDLE_RE.findall(message)
    return urls, handles


def extract_per_question(q: str) -> tuple[list[str], list[str]]:
    q_urls = _TIKTOK_URL_RE.findall(q)
    q_handles = _HANDLE_RE.findall(q)
    return q_urls, q_handles


def is_knowledge_question(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in KNOWLEDGE_SIGNALS)


def infer_niche_from_message(message: str) -> str:
    """Best-effort niche string for search/hashtag APIs."""
    m = re.search(r"\bin\s+([#a-zA-Z0-9_+]+)", message, re.IGNORECASE)
    if m:
        return m.group(1).lstrip("#").strip()
    m2 = re.search(r"#(\w+)", message)
    if m2:
        return m2.group(1).strip()
    cleaned = re.sub(r"https?://\S+", "", message).strip()
    cleaned = re.sub(r"@\w+", "", cleaned).strip()
    return (cleaned[:56] if cleaned else "tiktok").strip() or "tiktok"


def split_into_questions(message: str) -> list[str]:
    """Split multi-part user messages (e.g. '... Also, ...')."""
    raw = message.strip()
    if not raw:
        return []
    parts = re.split(r"\bAlso,|\n\n+", raw, flags=re.IGNORECASE)
    out = [p.strip() for p in parts if p.strip()]
    return out if out else [raw]


def classify_intent(
    message: str,
    urls: list[str],
    handles: list[str],
    has_session: bool,
) -> QueryIntent:
    msg = message.lower()
    has_urls = bool(urls)
    multi_urls = len(urls) > 1

    if multi_urls:
        return QueryIntent.SERIES_AUDIT

    if handles and not has_urls:
        return QueryIntent.COMPETITOR_PROFILE

    if any(
        kw in msg
        for kw in [
            "write a brief",
            "brief for",
            "content plan",
            "production brief",
            "create a brief",
            "brief me",
        ]
    ):
        return QueryIntent.BRIEF_GENERATION

    if has_urls and any(
        kw in msg
        for kw in ["stats", "metrics", "followers", "how many", "views on"]
    ) and not any(kw in msg for kw in ["analyze", "why", "what should", "what's wrong"]):
        return QueryIntent.METADATA_ONLY

    if has_urls and any(
        kw in msg
        for kw in [
            "analyze",
            "improve",
            "why",
            "flop",
            "views",
            "fix",
            "what should",
            "how did",
            "what's wrong",
            "better",
        ]
    ):
        return QueryIntent.VIDEO_DIAGNOSIS

    if any(
        kw in msg
        for kw in [
            "trending now",
            "trending",
            "blowing up",
            "this week",
            "right now",
            "latest",
            "new trend",
            "just dropped",
            "viral right now",
            "what's trending",
        ]
    ):
        return QueryIntent.TREND_SPIKE

    if not has_urls and any(
        kw in msg
        for kw in [
            "direction",
            "top",
            "popular",
            "what's working",
            "niche",
            "category",
            "how do",
            "what format",
            "structure",
        ]
    ):
        return QueryIntent.CONTENT_DIRECTIONS

    if not has_urls and has_session:
        return QueryIntent.FOLLOWUP

    return QueryIntent.VIDEO_DIAGNOSIS if has_urls else QueryIntent.CONTENT_DIRECTIONS


def detect_hybrid_intents(
    message: str,
    urls: list[str],
    handles: list[str],
) -> list[QueryIntent] | None:
    msg = message.lower()
    has_urls = bool(urls)
    has_handles = bool(handles)

    recency_signal = any(
        kw in msg
        for kw in [
            "right now",
            "this week",
            "blowing up",
            "trending now",
            "trending",
            "working now",
            "still working",
            "still relevant",
            "still worth",
            "latest",
            "just dropped",
            "viral right now",
            "what's trending",
        ]
    )

    structural_signal = any(
        kw in msg
        for kw in [
            "format",
            "hook",
            "structure",
            "carousel",
            "direction",
            "should i do",
            "which is better",
            "hooks are working",
        ]
    )

    brief_signal = any(
        kw in msg for kw in ["brief", "content plan", "production brief"]
    )

    if brief_signal and recency_signal and not has_urls:
        return [
            QueryIntent.TREND_SPIKE,
            QueryIntent.CONTENT_DIRECTIONS,
            QueryIntent.BRIEF_GENERATION,
        ]

    if has_urls and has_handles:
        return [QueryIntent.COMPETITOR_PROFILE, QueryIntent.VIDEO_DIAGNOSIS]

    if recency_signal and structural_signal and not has_urls:
        return [QueryIntent.TREND_SPIKE, QueryIntent.CONTENT_DIRECTIONS]

    return None


class CollapseResult:
    """Grouped intents plus any knowledge sub-questions extracted during collapsing."""

    __slots__ = ("pairs", "knowledge_questions")

    def __init__(
        self,
        pairs: list[tuple[QueryIntent, list[str]]],
        knowledge_questions: list[str],
    ) -> None:
        self.pairs = pairs
        self.knowledge_questions = knowledge_questions


def collapse_to_intents(
    questions: list[str],
    urls: list[str],
    handles: list[str],
    has_session: bool,
) -> CollapseResult:
    intent_groups: dict[QueryIntent, list[str]] = {}
    knowledge_qs: list[str] = []
    for q in questions:
        q_urls, q_handles = extract_per_question(q)
        if not q_urls and is_knowledge_question(q):
            knowledge_qs.append(q)
            continue
        hybrid = detect_hybrid_intents(q, q_urls, q_handles)
        if hybrid:
            for intent in hybrid:
                intent_groups.setdefault(intent, []).append(q)
            continue
        intent = classify_intent(q, q_urls, q_handles, has_session)
        intent_groups.setdefault(intent, []).append(q)

    order = [
        QueryIntent.TREND_SPIKE,
        QueryIntent.CONTENT_DIRECTIONS,
        QueryIntent.VIDEO_DIAGNOSIS,
        QueryIntent.COMPETITOR_PROFILE,
        QueryIntent.OWN_CHANNEL,
        QueryIntent.SERIES_AUDIT,
        QueryIntent.BRIEF_GENERATION,
        QueryIntent.SHOT_LIST,
        QueryIntent.FIND_CREATORS,
        QueryIntent.METADATA_ONLY,
        QueryIntent.FOLLOWUP,
    ]
    pairs = [(i, intent_groups[i]) for i in order if i in intent_groups]
    return CollapseResult(pairs, knowledge_qs)


def check_chain_dependencies(
    intent: QueryIntent,
    session_context: dict,
    handles: list[str] | None = None,
) -> list[QueryIntent]:
    base_dependencies: dict[QueryIntent, list[QueryIntent]] = {
        QueryIntent.VIDEO_DIAGNOSIS: [QueryIntent.CONTENT_DIRECTIONS],
        QueryIntent.SERIES_AUDIT: [QueryIntent.CONTENT_DIRECTIONS],
        QueryIntent.BRIEF_GENERATION: [
            QueryIntent.CONTENT_DIRECTIONS,
            QueryIntent.VIDEO_DIAGNOSIS,
        ],
    }
    required = list(base_dependencies.get(intent, []))

    done: set[str] = set()
    for x in session_context.get("completed_intents", []):
        done.add(x.value if isinstance(x, QueryIntent) else str(x))

    if (
        intent == QueryIntent.VIDEO_DIAGNOSIS
        and handles
        and QueryIntent.COMPETITOR_PROFILE.value not in done
    ):
        required.append(QueryIntent.COMPETITOR_PROFILE)

    return [r for r in required if r.value not in done]

