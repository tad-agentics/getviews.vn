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
    # Phase C §A.2 — `/answer` report intents (classify_intent + Gemini)
    SUBNICHE_BREAKDOWN = "subniche_breakdown"
    FORMAT_LIFECYCLE_OPTIMIZE = "format_lifecycle_optimize"
    FATIGUE = "fatigue"
    HOOK_VARIANTS = "hook_variants"
    TIMING = "timing"
    CONTENT_CALENDAR = "content_calendar"
    COMPARISON = "comparison"
    FOLLOW_UP_CLASSIFIABLE = "follow_up_classifiable"
    FOLLOW_UP_UNCLASSIFIABLE = "follow_up_unclassifiable"


KNOWLEDGE_SIGNALS = [
    # English
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
    # Vietnamese equivalents
    "thuật toán",
    "tiktok hoạt động",
    "tiktok phạt",
    "shadowban",
    "có đáng",
    "đăng nhiều",
    "từ khóa",
    "hashtag",
    "caption",
    "bình luận mồi",
    "gây tranh cãi",
    "hack thuật toán",
    "đèn ring",
    "microphone",
    "thiết bị",
    "ánh sáng",
    "chất lượng sản xuất",
    "điện thoại vs",
    "máy ảnh vs",
]

_TIKTOK_URL_RE = re.compile(
    # Matches full TikTok URLs (www.tiktok.com, tiktok.com) and all short-link
    # domains (vm.tiktok.com, vt.tiktok.com, and any future *.tiktok.com variants).
    r"https?://(?:(?:www\.)?tiktok\.com|(?:vm|vt|m)\.tiktok\.com)/\S+",
    re.IGNORECASE,
)
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


def extract_per_question(q: str) -> tuple[list[str], list[str]]:
    q_urls = _TIKTOK_URL_RE.findall(q)
    q_handles = _HANDLE_RE.findall(_strip_urls(q))
    return q_urls, q_handles


def is_knowledge_question(message: str) -> bool:
    msg = message.lower()
    return any(kw in msg for kw in KNOWLEDGE_SIGNALS)


def infer_niche_from_message(message: str) -> str:
    """Best-effort niche string for search/hashtag APIs.

    Handles both English ("in fitness") and Vietnamese
    ("trong niche skincare", "niche mỹ phẩm", "lĩnh vực ẩm thực") patterns.
    """
    # English: "in <niche>"
    m = re.search(r"\bin\s+([#a-zA-Z0-9_+\u00C0-\u024F\u1E00-\u1EFF]+)", message, re.IGNORECASE)
    if m:
        return m.group(1).lstrip("#").strip()
    # Vietnamese: "trong niche X" / "niche X" / "trong lĩnh vực X"
    m_vi = re.search(
        r"(?:trong\s+)?(?:niche|lĩnh vực|ngách|chủ đề)\s+([^\s,.!?]+)",
        message,
        re.IGNORECASE,
    )
    if m_vi:
        return m_vi.group(1).lstrip("#").strip()
    m2 = re.search(r"#(\w+)", message)
    if m2:
        return m2.group(1).strip()
    cleaned = re.sub(r"https?://\S+", "", message).strip()
    cleaned = re.sub(r"@\w+", "", cleaned).strip()
    return (cleaned[:56] if cleaned else "tiktok").strip() or "tiktok"


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
            # English
            "write a brief",
            "brief for",
            "content plan",
            "production brief",
            "create a brief",
            "brief me",
            # Vietnamese
            "viết brief",
            "tạo brief",
            "lên kế hoạch nội dung",
            "kế hoạch content",
            "brief cho",
            "brief nội dung",
        ]
    ):
        return QueryIntent.BRIEF_GENERATION

    if has_urls and any(
        kw in msg
        for kw in [
            # English
            "stats", "metrics", "followers", "how many", "views on",
            # Vietnamese
            "lượt xem", "người theo dõi", "bao nhiêu view", "bao nhiêu follow",
            "chỉ số", "số liệu",
        ]
    ) and not any(kw in msg for kw in [
        # English negation
        "analyze", "why", "what should", "what's wrong",
        # Vietnamese negation
        "phân tích", "tại sao", "vì sao", "nên làm gì", "sai ở đâu",
    ]):
        return QueryIntent.METADATA_ONLY

    if has_urls and any(
        kw in msg
        for kw in [
            # English
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
            # Vietnamese
            "phân tích",
            "cải thiện",
            "tại sao",
            "vì sao",
            "ít view",
            "sửa",
            "nên làm gì",
            "làm thế nào",
            "sai ở đâu",
            "tốt hơn",
            "tại sao video",
            "video này",
        ]
    ):
        return QueryIntent.VIDEO_DIAGNOSIS

    if any(
        kw in msg
        for kw in [
            # English
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
            # Vietnamese
            "đang trending",
            "xu hướng",
            "đang hot",
            "đang lên",
            "tuần này",
            "hôm nay",
            "mới nhất",
            "viral",
            "bùng nổ",
            "đang nổi",
        ]
    ):
        return QueryIntent.TREND_SPIKE

    # Phase C — timing (posting windows)
    if not has_urls and any(
        kw in msg
        for kw in [
            "đăng giờ nào",
            "giờ nào tốt",
            "thứ mấy",
            "best time to post",
            "when to post",
            "posting time",
            "khung giờ",
            "lịch đăng",
        ]
    ):
        return QueryIntent.TIMING

    # Phase C — fatigue / declining patterns
    if not has_urls and any(
        kw in msg
        for kw in [
            "pattern hết",
            "hết trend",
            "đang chết",
            "đang giảm dần",
            "không còn hiệu",
            "dead trend",
            "declining format",
        ]
    ):
        return QueryIntent.FATIGUE

    # Phase C — format length / carousel vs video
    if not has_urls and any(
        kw in msg
        for kw in [
            "30s vs 60",
            "60s vs 30",
            "carousel vs video",
            "ảnh vs video",
            "short vs long",
            "độ dài video",
        ]
    ):
        return QueryIntent.FORMAT_LIFECYCLE_OPTIMIZE

    # Phase C — hook variant requests
    if not has_urls and any(
        kw in msg
        for kw in [
            "biến thể của hook",
            "hook variants",
            "5 cách viết hook",
            "cách viết hook này",
            "viết lại hook",
        ]
    ):
        return QueryIntent.HOOK_VARIANTS

    # Phase C — weekly content calendar
    if not has_urls and any(
        kw in msg
        for kw in [
            "tuần này post gì",
            "lịch content tuần",
            "content calendar",
            "khi nào post gì",
        ]
    ):
        return QueryIntent.CONTENT_CALENDAR

    # Phase C — sub-niche breakdown (explicit)
    if not has_urls and any(
        kw in msg
        for kw in [
            "ngách con",
            "subniche",
            "sub-niche",
            "phân ngách",
        ]
    ):
        return QueryIntent.SUBNICHE_BREAKDOWN

    # Phase C — A vs B creators (2+ handles, compare framing)
    if len(handles) >= 2 and any(
        kw in msg
        for kw in ["so sánh", "compare", "vs ", "versus", "hay hơn", "ai hơn"]
    ):
        return QueryIntent.COMPARISON

    if not has_urls and any(
        kw in msg
        for kw in [
            # English
            "direction",
            "top",
            "popular",
            "what's working",
            "niche",
            "category",
            "how do",
            "what format",
            "structure",
            # Vietnamese
            "hướng nội dung",
            "nên làm",
            "video gì",
            "format nào",
            "loại video",
            "ý tưởng",
            "chủ đề",
            "niche",
            "đang hoạt động",
            "cấu trúc",
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
            # English
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
            # Vietnamese
            "tuần này",
            "hôm nay",
            "đang trending",
            "đang hot",
            "đang lên",
            "xu hướng",
            "viral",
            "bùng nổ",
            "đang nổi",
            "mới nhất",
            "còn hoạt động",
            "vẫn hiệu quả",
        ]
    )

    structural_signal = any(
        kw in msg
        for kw in [
            # English
            "format",
            "hook",
            "structure",
            "carousel",
            "direction",
            "should i do",
            "which is better",
            "hooks are working",
            # Vietnamese
            "format",
            "hook",
            "cấu trúc",
            "carousel",
            "hướng nội dung",
            "nên làm gì",
            "cái nào tốt hơn",
            "hook nào",
        ]
    )

    # Directions signal: user wants content format/direction suggestions in addition to diagnosis.
    # Broader than structural_signal — catches "gợi ý", "định dạng", "niche liên quan", etc.
    directions_signal = any(
        kw in msg
        for kw in [
            # English
            "suggest", "content ideas", "content directions", "content formats",
            "what formats", "ideas for", "ideas from",
            # Vietnamese
            "gợi ý", "định dạng nội dung", "hướng nội dung", "các định dạng",
            "nghiên cứu từ niche", "niche liên quan", "mảng liên quan",
            "format nào", "ý tưởng nội dung", "loại nội dung",
        ]
    )

    brief_signal = any(
        kw in msg for kw in [
            # English
            "brief", "content plan", "production brief",
            # Vietnamese
            "brief", "kế hoạch content", "kế hoạch nội dung", "lên kế hoạch",
        ]
    )

    # Diagnosis + directions: URL present, user asks WHY it underperforms AND wants content ideas.
    # CONTENT_DIRECTIONS runs first (collapse order) so niche context is in session before diagnosis.
    if has_urls and directions_signal and any(
        kw in msg
        for kw in [
            # English
            "why", "low views", "few views", "not performing", "underperforming",
            "what's wrong", "fix", "improve",
            # Vietnamese
            "tại sao", "vì sao", "ít view", "ít views", "không lên", "sai ở đâu",
            "cải thiện", "sửa", "nên làm gì",
        ]
    ):
        return [QueryIntent.CONTENT_DIRECTIONS, QueryIntent.VIDEO_DIAGNOSIS]

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
        QueryIntent.SUBNICHE_BREAKDOWN,
        QueryIntent.FORMAT_LIFECYCLE_OPTIMIZE,
        QueryIntent.FATIGUE,
        QueryIntent.TIMING,
        QueryIntent.CONTENT_CALENDAR,
        QueryIntent.HOOK_VARIANTS,
        QueryIntent.BRIEF_GENERATION,
        QueryIntent.VIDEO_DIAGNOSIS,
        QueryIntent.COMPETITOR_PROFILE,
        QueryIntent.COMPARISON,
        QueryIntent.OWN_CHANNEL,
        QueryIntent.SERIES_AUDIT,
        QueryIntent.SHOT_LIST,
        QueryIntent.FIND_CREATORS,
        QueryIntent.METADATA_ONLY,
        QueryIntent.FOLLOW_UP_CLASSIFIABLE,
        QueryIntent.FOLLOW_UP_UNCLASSIFIABLE,
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

