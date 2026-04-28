"""Video diagnosis report builder for the answer surface.

Bridges ``answer_session.append_turn`` (the central answer-session
dispatcher) to the existing ``run_video_analyze_pipeline`` /
``run_video_analyze_on_demand`` machinery. Extracts the TikTok URL
from the user's query, runs the analysis through the corpus path,
falls through to the on-demand path on miss (mirrors the
``/video/analyze`` endpoint's fallback wired in PR #286). Returns
the ``VideoAnalyzeResponse``-shaped dict; ``answer_session`` then
hands it to ``validate_and_store_report("video", ...)`` to land in
``answer_turns.payload`` as a ``ReportV1`` envelope.

PR-2 ships dark — the composer still redirects URL pastes to
``/app/video``, so this builder is unreachable in production until
PR-3 flips ``INTENT_DESTINATIONS.video_diagnosis``. Tests exercise
it directly by calling ``build_video_report`` so the dark code
isn't unverified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from getviews_pipeline.video_analyze import (
    run_video_analyze_on_demand,
    run_video_analyze_pipeline,
)

logger = logging.getLogger(__name__)


# Match TikTok URLs the same way the FE intent-router does. Covers
# www.tiktok.com, m.tiktok.com, and the vm.tiktok.com short-link
# format (the post_info endpoint follows redirects, so the short
# URL works as a /video/analyze input as long as we extract it
# verbatim).
_TIKTOK_URL_RE = re.compile(
    r"https?://(?:www\.|m\.|vm\.)?tiktok\.com/[^\s]+",
    re.IGNORECASE,
)

# TikTok aweme_ids are 19-digit numeric strings. Standalone matching
# (no surrounding URL) covers PR-3's evidence-tile clicks: those tiles
# only carry the bare ``video_id`` from the corpus row, not a full
# URL. We accept the id alongside URLs so the same builder serves
# both code paths (``state.prefillUrl = "https://..."`` and
# ``state.prefillUrl = "<aweme_id>"``).
_AWEME_ID_RE = re.compile(r"\b(\d{15,21})\b")


def extract_tiktok_url(query: str) -> str | None:
    """Pull the first TikTok URL out of a free-form Vietnamese query.

    The session intent is ``video_diagnosis`` only when the FE
    classifier saw a URL — but the query is the raw user message
    ("tại sao video này không có view + URL"), so we still need to
    parse it back out for the BE call.
    """
    if not query:
        return None
    m = _TIKTOK_URL_RE.search(query)
    return m.group(0) if m else None


def extract_aweme_id(query: str) -> str | None:
    """Pull a bare TikTok ``aweme_id`` (numeric video_id) out of the
    query when no URL is present. Used by the evidence-tile click
    path: corpus rows expose ``video_id`` but the FE click site
    doesn't always have the creator handle to build a tiktok_url.

    Returns the first 15-21 digit run that isn't part of a URL match.
    Caller must check ``extract_tiktok_url`` first — this function
    blindly returns the digit run regardless of any URL also present.
    """
    if not query:
        return None
    m = _AWEME_ID_RE.search(query)
    return m.group(1) if m else None


# Vietnamese phrase signals for win/flop intent. Patterns cover the
# common creator phrasings observed in /app/answer prompts:
#
#   Flop:  "không có view", "ít view", "view thấp", "không nổ",
#          "tại sao flop", "video flop", "vì sao kém", "không lên",
#          "video tệ", "không lên xu hướng"
#   Win:   "viral", "video nổ", "tại sao nổ", "nhiều view",
#          "vì sao thành công", "lên top", "lên xu hướng",
#          "tại sao lên trending"
#
# Detection runs against the lower-cased query. Tie (both sets match)
# returns None so the BE heuristic (``is_flop_mode``) makes the call.
_FLOP_SIGNALS = (
    re.compile(r"\b(không|chưa)\s+có\s+view", re.IGNORECASE),
    re.compile(r"\bít\s+view\b", re.IGNORECASE),
    re.compile(r"\bview\s+thấp\b", re.IGNORECASE),
    re.compile(r"\b(không|chưa)\s+nổ\b", re.IGNORECASE),
    re.compile(r"\b(không|chưa)\s+lên\b", re.IGNORECASE),
    re.compile(r"\b(không|chưa)\s+lên\s+xu\s+hướng\b", re.IGNORECASE),
    re.compile(r"\b(không|chưa)\s+lên\s+trending\b", re.IGNORECASE),
    re.compile(r"\bflop\b", re.IGNORECASE),
    re.compile(r"\bvideo\s+kém\b", re.IGNORECASE),
    re.compile(r"\bvideo\s+tệ\b", re.IGNORECASE),
    re.compile(r"\b(tại|vì)\s+sao\s+kém\b", re.IGNORECASE),
    re.compile(r"\b(tại|vì)\s+sao\s+(không|chưa)\s+nổ\b", re.IGNORECASE),
)
# Negative lookbehinds prevent the win patterns from matching when
# preceded by a Vietnamese negation ("không lên xu hướng" should be
# flop, not win-with-tie). Python's re supports fixed-width
# lookbehinds; ``không `` is 6 chars, ``chưa `` is 5 chars — both
# fixed, so two separate ``(?<!...)`` clauses do the job.
_NEG_LOOKBEHINDS = r"(?<!không\s)(?<!chưa\s)"
_WIN_SIGNALS = (
    re.compile(r"\bviral\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\bvideo\s+nổ\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\bnhiều\s+view\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\b(tại|vì)\s+sao\s+nổ\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\b(tại|vì)\s+sao\s+(thành\s+công|nhiều\s+view)\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\blên\s+(top|xu\s+hướng|trending)\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\b(tại|vì)\s+sao\s+lên\s+(top|xu\s+hướng|trending)\b", re.IGNORECASE),
    re.compile(rf"{_NEG_LOOKBEHINDS}\bvideo\s+thành\s+công\b", re.IGNORECASE),
)


def detect_mode_from_query(query: str) -> str | None:
    """Pull a win/flop hint out of the user's accompanying text.

    The video-as-template migration preserved the user's full message
    as the answer-session ``initial_q``. So when a creator pastes
    ``tại sao video này không có view + URL``, the BE can read that
    intent directly instead of relying on the niche-cohort heuristic
    (which gets it wrong when there's no cohort to compare against).

    Returns ``"win"``, ``"flop"``, or ``None`` (no signal or
    contradictory signals — let ``is_flop_mode`` decide). Word
    boundaries are conservative; novel phrasings will fall through
    to the heuristic until we add them. Acceptable trade-off:
    keyword-based detection is predictable + auditable, vs LLM
    classification which is opaque + costs tokens per turn.
    """
    if not query:
        return None
    flop_hit = any(p.search(query) for p in _FLOP_SIGNALS)
    win_hit = any(p.search(query) for p in _WIN_SIGNALS)
    if flop_hit and win_hit:
        return None  # Contradictory — defer to heuristic.
    if flop_hit:
        return "flop"
    if win_hit:
        return "win"
    return None


def build_video_report(
    *,
    service_sb: Any,
    user_sb: Any,
    query: str,
    mode: str | None = None,
) -> dict[str, Any]:
    """Build a ``VideoAnalyzeResponse``-shaped dict for an answer turn.

    Strategy mirrors ``routers/video.video_analyze_endpoint``:
      1. Extract the URL from the query.
      2. Try the corpus path (``run_video_analyze_pipeline``) — fast
         if the URL is in ``video_corpus``, with cached diagnostics.
      3. On corpus miss (ValueError), fall through to the on-demand
         path (``run_video_analyze_on_demand``) — fresh fetch + Gemini
         analysis, no corpus write.

    Returns the response dict augmented with empty ``sources`` and
    ``related_questions`` so the answer-shell readers
    (``AnswerSourcesCard``, ``RelatedQs``) type-narrow cleanly. PR-2
    leaves these empty; a follow-up could populate
    ``related_questions`` with niche-aware suggestions.

    Raises ``ValueError`` when the query has no parseable TikTok URL
    or aweme_id (caller → 400) or when both corpus + on-demand paths
    miss in a way that can't be analysed (e.g. invalid URL shape).
    """
    url = extract_tiktok_url(query)
    aweme_id = extract_aweme_id(query) if not url else None
    if not url and not aweme_id:
        raise ValueError("Không tìm thấy link TikTok trong câu hỏi")

    # Mode resolution priority:
    #   1. Caller-supplied ``mode`` (explicit win/flop override).
    #   2. Vietnamese keyword detection from the user's accompanying
    #      text — when the creator says "tại sao không có view", we
    #      respect that intent instead of letting the niche heuristic
    #      flip it.
    #   3. None → BE ``is_flop_mode`` heuristic decides (niche cohort
    #      comparison + niche-less absolute thresholds).
    resolved_mode: str | None = mode if mode in ("win", "flop") else None
    if resolved_mode is None:
        resolved_mode = detect_mode_from_query(query)
        if resolved_mode is not None:
            logger.info(
                "[report_video] mode hint from query: %s", resolved_mode,
            )

    try:
        out = run_video_analyze_pipeline(
            service_sb,
            user_sb,
            video_id=aweme_id,
            tiktok_url=url,
            force_refresh=False,
            mode=resolved_mode,  # type: ignore[arg-type]
        )
    except ValueError as exc:
        msg = str(exc)
        # Mirrors the routers/video.py fallback decision: only the
        # "URL not in corpus" branch falls through; UUID lookups and
        # malformed inputs still raise.
        url_miss = (
            msg == "video not in corpus"
            or "Không tìm thấy video trong corpus cho URL này" in msg
        )
        if not url_miss:
            raise
        # On-demand path needs a real URL — bare aweme_id can't be
        # fetched without first knowing the creator handle. So an
        # aweme_id-only request that misses corpus is a hard 404.
        if not url:
            raise ValueError(
                "Không tìm thấy video trong corpus cho id này"
            ) from exc
        logger.info("[report_video] corpus miss → on-demand path url=%s", url)
        out = run_video_analyze_on_demand(
            service_sb,
            user_sb,
            tiktok_url=url,
            mode=resolved_mode,  # type: ignore[arg-type]
        )

    # Add the answer-shell common fields. ``sources`` empty because a
    # one-video diagnosis has no comparison cohort to cite;
    # ``related_questions`` empty for v1 (PR-3 follow-up could
    # populate from niche playbook).
    out.setdefault("sources", [])
    out.setdefault("related_questions", [])
    return out
