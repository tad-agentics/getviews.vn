"""Comment sentiment + purchase-intent radar.

Pure regex scorer over Vietnamese TikTok comment text, plus a thin wrapper
around EnsembleData's /tt/post/comments endpoint. See the spec at
artifacts/docs/features/comment-sentiment.md.

Four signals per video:

  sentiment     — positive_pct / negative_pct / neutral_pct (share of sampled
                  comments hitting each bucket; "no match" → neutral)
  purchase_intent.count + top_phrases — commerce signal sellers care about:
                  "tôi sẽ mua", "link đâu", "giá bao nhiêu"
  questions_asked — comments containing a question mark or classic VN
                  question words
  language      — "vi" | "mixed" | "non-vi" (for rendering decisions; a
                  non-Vietnamese-skew audience is itself a signal)

Fail-soft design: the scorer returns a valid (possibly-empty) radar even
when given garbage input. fetch_comments fails open — returns [] on
quota / HTTP errors so callers never block.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Regex banks
# ---------------------------------------------------------------------------

# Vietnamese-first, with English fallbacks sellers' global audiences leave.

PURCHASE_INTENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE)
    for p in (
        r"\btôi\s+sẽ\s+(mua|thử|order|đặt)",
        r"\bmình\s+sẽ\s+(mua|thử|order|đặt)",
        r"\b(cần|muốn|thích)\s+(mua|thử|order|sở\s*hữu)",
        r"\b(giá|price)\s+(bao\s*nhiêu|sao|ntn|thế\s*nào)",
        r"\b(bao\s*nhiêu|nhiêu)\s+(tiền|vậy|ạ|vnd|đồng)",
        r"\blink\s*(đâu|bio|shopee|tiktok\s*shop|trong)",
        r"\b(đặt|order|mua)\s+(ở\s+)?(đâu|where)",
        r"\bshopee|\btiktok\s*shop|\blazada",
        r"\bshop\s+(ở|bán|có|nào)",
        r"\bdm|\binbox\s+(mình|e|em|shop)",
        r"\bwhere\s+to\s+(buy|get|order)",
        r"\bhow\s+much",
        r"\bi\s+('ll|will)\s+buy",
    )
)

POSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE)
    for p in (
        r"\b(đỉnh|tuyệt\s*vời|xuất\s*sắc|xịn\s*xò|chất\s*lượng)",
        r"\bhay\s+(quá|vl|thật)",
        r"\b(thích|mê|iu|yêu)\s+(quá|lắm|ghê|cực)",
        r"\b(hữu\s*ích|bổ\s*ích|học\s+được|có\s+lý)",
        r"\bchuẩn\s+(luôn|rồi|vl)",
        r"\b(ngầu|xinh|đẹp)\s+(vl|vcl|quá|ghê)",
        r"\b(awesome|amazing|love\s+this|so\s+good)\b",
    )
)

# Emoji positive signals — quick single-code-point set, don't regex.
_POSITIVE_EMOJI: frozenset[str] = frozenset("❤😍🔥💯👏😘🥰❤️")
_NEGATIVE_EMOJI: frozenset[str] = frozenset("👎🤮😒💀🙄")

NEGATIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE)
    for p in (
        r"\b(lừa\s*đảo|scam|fake|hàng\s*giả)",
        r"\b(không|chả|éo)\s+(tin|dùng)",
        r"\bhoang\s*đường",
        r"\b(dở|chán|tệ|nhảm|vớ\s*vẩn)",
        r"\b(phí\s+(tiền|thời\s*gian))",
        r"\bspam\b|\bclickbait\b",
        r"\bwaste\s+of\s+(time|money)\b",
    )
)

QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE)
    for p in (
        r"\bgiá\b", r"\blink\b",
        r"\b(ở\s+đâu|where)\b",
        r"\b(có\s+)?(shop|bán|store)\b",
        r"\bbao\s+nhiêu\b",
    )
)

# Spam / bot — used to down-sample noise before scoring. We don't reject
# comments entirely, but we give them zero weight so a bot farm can't skew the
# sentiment.
_SPAM_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.UNICODE)
    for p in (
        r"^(?:[\W_]|\s)*$",           # pure symbols/whitespace
        r"^[a-z]{1,3}$",              # single-token typo ("ok", "hi")
        r"^\s*\d+\s*$",               # just a number
    )
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommentRadar:
    sampled: int
    total_available: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    purchase_intent_count: int
    purchase_intent_phrases: tuple[str, ...]
    questions_asked: int
    language: str    # "vi" | "mixed" | "non-vi" | "unknown"

    def asdict(self) -> dict[str, Any]:
        return {
            "sampled": self.sampled,
            "total_available": self.total_available,
            "sentiment": {
                "positive_pct": round(self.positive_pct, 1),
                "negative_pct": round(self.negative_pct, 1),
                "neutral_pct": round(self.neutral_pct, 1),
            },
            "purchase_intent": {
                "count": self.purchase_intent_count,
                "top_phrases": list(self.purchase_intent_phrases),
            },
            "questions_asked": self.questions_asked,
            "language": self.language,
        }

    @classmethod
    def empty(cls, total_available: int = 0) -> "CommentRadar":
        return cls(
            sampled=0,
            total_available=total_available,
            positive_pct=0.0,
            negative_pct=0.0,
            neutral_pct=0.0,
            purchase_intent_count=0,
            purchase_intent_phrases=(),
            questions_asked=0,
            language="unknown",
        )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


_VI_DIACRITIC_CHARS: frozenset[int] = frozenset(range(0x0300, 0x036F + 1))
_VI_SPECIAL_LETTERS: frozenset[str] = frozenset("đĐ")


def _is_spammy(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True
    if any(p.match(s) for p in _SPAM_PATTERNS):
        return True
    # >80% emoji → spam (bot farms often flood with ❤️❤️❤️).
    if len(s) > 0:
        emoji_count = sum(1 for c in s if (c in _POSITIVE_EMOJI or c in _NEGATIVE_EMOJI))
        if emoji_count / len(s) > 0.8 and len(s) >= 3:
            return True
    return False


def _has_vietnamese(text: str) -> bool:
    if not text:
        return False
    nfkd = unicodedata.normalize("NFKD", text)
    if any(ord(c) in _VI_DIACRITIC_CHARS for c in nfkd):
        return True
    return any(c in _VI_SPECIAL_LETTERS for c in text)


def _match_any(patterns: Iterable[re.Pattern[str]], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def _has_positive_emoji(text: str) -> bool:
    return any(c in _POSITIVE_EMOJI for c in text)


def _has_negative_emoji(text: str) -> bool:
    return any(c in _NEGATIVE_EMOJI for c in text)


def _normalize_phrase(text: str, limit: int = 80) -> str:
    """Strip @handles and URLs, collapse whitespace, truncate to limit."""
    s = re.sub(r"@\w+", "", text)
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s


def score_comments(
    comments: Iterable[str],
    *,
    total_available: int | None = None,
    sample_cap: int = 50,
) -> CommentRadar:
    """Reduce a bag of Vietnamese TikTok comments to a compact `CommentRadar`.

    The scorer does not keep per-comment state beyond the purchase-intent top
    phrases — everything else is aggregate counts. This keeps the downstream
    payload small and privacy-light.

    Precedence per comment:
      1. Spam / empty          → skip (no contribution to denominator)
      2. Purchase intent hit   → counts toward intent AND positive sentiment
      3. Positive keyword/emoji
      4. Negative keyword/emoji
      5. Question pattern      → counts toward questions_asked (can also be +/-)
      6. No match              → neutral
    """
    comment_list = [str(c) for c in comments if c]
    if total_available is None:
        total_available = len(comment_list)

    # Optional sample cap — respect caller's intent if already-trimmed.
    if sample_cap and len(comment_list) > sample_cap:
        comment_list = comment_list[:sample_cap]

    if not comment_list:
        return CommentRadar.empty(total_available=total_available)

    sampled = 0
    positive = 0
    negative = 0
    neutral = 0
    intent_count = 0
    questions = 0
    intent_phrases: list[str] = []

    vi_hits = 0

    for raw in comment_list:
        if _is_spammy(raw):
            continue
        sampled += 1
        text = raw.strip()

        if _has_vietnamese(text):
            vi_hits += 1

        is_intent = _match_any(PURCHASE_INTENT_PATTERNS, text)
        is_positive = is_intent or _match_any(POSITIVE_PATTERNS, text) or _has_positive_emoji(text)
        is_negative = _match_any(NEGATIVE_PATTERNS, text) or _has_negative_emoji(text)
        is_question = "?" in text or _match_any(QUESTION_PATTERNS, text)

        if is_intent:
            intent_count += 1
            if len(intent_phrases) < 3:
                phrase = _normalize_phrase(text)
                if phrase and phrase not in intent_phrases:
                    intent_phrases.append(phrase)
        if is_question:
            questions += 1

        if is_positive and not is_negative:
            positive += 1
        elif is_negative and not is_positive:
            negative += 1
        elif is_positive and is_negative:
            # Mixed signal — record both, count as neutral for sentiment bucket.
            neutral += 1
        else:
            neutral += 1

    if sampled == 0:
        return CommentRadar.empty(total_available=total_available)

    pos_pct = 100.0 * positive / sampled
    neg_pct = 100.0 * negative / sampled
    neu_pct = 100.0 * neutral / sampled
    vi_ratio = vi_hits / sampled
    if vi_ratio >= 0.7:
        language = "vi"
    elif vi_ratio >= 0.3:
        language = "mixed"
    elif vi_ratio > 0:
        language = "non-vi"
    else:
        language = "non-vi"

    return CommentRadar(
        sampled=sampled,
        total_available=total_available,
        positive_pct=pos_pct,
        negative_pct=neg_pct,
        neutral_pct=neu_pct,
        purchase_intent_count=intent_count,
        purchase_intent_phrases=tuple(intent_phrases),
        questions_asked=questions,
        language=language,
    )


# ---------------------------------------------------------------------------
# EnsembleData fetch wrapper
# ---------------------------------------------------------------------------


async def fetch_comments_for_video(video_id: str, *, max_comments: int = 50) -> list[str]:
    """Thin wrapper around EnsembleData /tt/post/comments.

    Fails open on any error — returns []. Caller composes with score_comments()
    to produce a CommentRadar. Cap at 50 comments so one fetch stays inside a
    single EnsembleData unit regardless of page size.

    Returns a list of raw comment text strings (we don't persist commenter
    identity beyond the comment body — §privacy).
    """
    vid = str(video_id or "").strip()
    if not vid:
        return []
    try:
        # Imported lazily so unit tests for score_comments don't drag in ensemble.
        from getviews_pipeline import ensemble
        from getviews_pipeline.config import ENSEMBLEDATA_POST_COMMENTS_URL

        payload = await ensemble._ensemble_get(
            ENSEMBLEDATA_POST_COMMENTS_URL,
            {"aweme_id": vid, "cursor": 0},
        )
    except Exception as exc:
        logger.warning("[comment_radar] fetch_comments_for_video(%s) failed: %s", vid, exc)
        return []

    data = payload.get("data") if isinstance(payload, dict) else None
    rows: list[dict[str, Any]] = []
    if isinstance(data, dict):
        rows = data.get("comments") or data.get("list") or data.get("data") or []
        if not isinstance(rows, list):
            rows = []
    elif isinstance(data, list):
        rows = data

    out: list[str] = []
    for row in rows[:max_comments]:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or row.get("content") or row.get("comment") or "").strip()
        if text:
            out.append(text)
    return out


__all__ = [
    "CommentRadar",
    "fetch_comments_for_video",
    "score_comments",
]
