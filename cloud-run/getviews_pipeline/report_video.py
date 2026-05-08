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

Also handles bare aweme_ids passed from ``EvidenceThumbs`` (IdeaBlock):
``detect_intent`` classifies a bare 15-20 digit string as
``video_diagnosis`` so ``answer_session`` routes here; ``extract_aweme_id``
picks up the id and routes to the corpus path.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from getviews_pipeline.url_patterns import TIKTOK_URL_RE
from getviews_pipeline.video_analyze import (
    run_video_analyze_on_demand,
    run_video_analyze_pipeline,
)

logger = logging.getLogger(__name__)


# L1.5 — canonical pattern lives in url_patterns. The previous local
# regex was missing vt.tiktok.com support, which let intent classification
# accept vt-links that this builder couldn't extract — silent dead-end.
_TIKTOK_URL_RE = TIKTOK_URL_RE

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
    step_queue: asyncio.Queue | None = None,
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

    ``step_queue`` — optional; live SSE step events (reserved).
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

    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_status, step_tool_start

        emit(step_queue, step_status(1, "Đang tải video và tìm trong corpus..."))
        emit(step_queue, step_tool_start("Tra cứu corpus", 1, 0, tool="corpus"))

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

    if step_queue is not None:
        from getviews_pipeline.step_events import emit, step_done, step_status, step_tool_complete, step_tool_start

        meta = out.get("meta") or {}
        thumbs: list[str] = []
        tu = meta.get("thumbnail_url")
        if isinstance(tu, str) and tu.strip():
            thumbs.append(tu.strip())
        emit(step_queue, step_tool_complete(1, 0, 1, thumbs, tool="corpus"))
        creator = str(meta.get("creator") or "").strip()
        creator_lbl = f"@{creator}" if creator else "@creator"
        emit(step_queue, step_status(2, "Đang so sánh với video khác của creator..."))
        emit(step_queue, step_tool_start(creator_lbl, 2, 0, tool="search"))
        emit(step_queue, step_tool_complete(2, 0, 0, [], tool="search"))
        emit(step_queue, step_status(3, "Đang chạy Gemini phân tích frame..."))
        emit(step_queue, step_tool_start("Phân tích 6 frame video", 3, 0, tool="synthesis"))
        emit(step_queue, step_tool_complete(3, 0, 0, [], tool="synthesis"))
        emit(step_queue, step_done("Xong — đang hiển thị kết quả..."))

    return out
