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

    try:
        out = run_video_analyze_pipeline(
            service_sb,
            user_sb,
            video_id=aweme_id,
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
            mode=mode if mode in ("win", "flop") else None,  # type: ignore[arg-type]
        )

    # Add the answer-shell common fields. ``sources`` empty because a
    # one-video diagnosis has no comparison cohort to cite;
    # ``related_questions`` empty for v1 (PR-3 follow-up could
    # populate from niche playbook).
    out.setdefault("sources", [])
    out.setdefault("related_questions", [])
    return out
