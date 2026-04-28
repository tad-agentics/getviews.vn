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
    (caller → 400) or when both corpus + on-demand paths miss in a
    way that can't be analysed (e.g. invalid URL shape).
    """
    url = extract_tiktok_url(query)
    if not url:
        raise ValueError("Không tìm thấy link TikTok trong câu hỏi")

    try:
        out = run_video_analyze_pipeline(
            service_sb,
            user_sb,
            video_id=None,
            tiktok_url=url,
            force_refresh=False,
            mode=mode if mode in ("win", "flop") else None,  # type: ignore[arg-type]
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
        logger.info("[report_video] corpus miss → on-demand path url=%s", url)
        out = run_video_analyze_on_demand(
            service_sb,
            user_sb,
            tiktok_url=url,
            mode=mode if mode in ("win", "flop") else None,  # type: ignore[arg-type]
        )

    # Add the answer-shell common fields. ``sources`` empty because a
    # one-video diagnosis has no comparison cohort to cite;
    # ``related_questions`` empty for v1 (PR-3 follow-up could
    # populate from niche playbook).
    out.setdefault("sources", [])
    out.setdefault("related_questions", [])
    return out
