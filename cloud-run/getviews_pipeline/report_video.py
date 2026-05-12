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

from getviews_pipeline.report_types import CreatorComparison, CreatorComparisonVideo
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


async def build_creator_comparison(
    creator_handle: str,
    target_video_id: str,
    target_views: int,
    *,
    step_queue: asyncio.Queue | None = None,
) -> CreatorComparison | None:
    """Fetch creator recent posts; pick hit/flop vs median. Returns None on miss.

    Bug-fix (2026-05-08) — every video_diagnosis turn over the prior 14 days
    rendered without the SO SÁNH TRONG KÊNH card because this function
    returned None silently. Two changes:
      1. The ``len(parsed) < 3`` gate is lowered to ``< 2`` — a single
         hit + single flop is still a valid comparison; requiring three
         was too strict against EnsembleData's noisy ``play_count: 0``
         responses for fresh / private posts.
      2. Every early-return now emits a structured WARNING with a
         ``reason`` tag so we can diagnose subsequent misses from
         Cloud Run logs without re-deploying.

    Also applies the zero-views guard already deployed for
    ``find_ab_pair`` (audit Pass 2): a flop with < 100 views is treated
    as too noisy to anchor a delta — we filter it out of consideration
    rather than letting it fabricate a misleading multiplier.
    """

    from getviews_pipeline.ensemble import fetch_user_posts
    from getviews_pipeline.step_events import emit, step_tool_complete, step_tool_start

    def _miss(reason: str, **details: Any) -> None:
        """Log + emit the empty tool_complete card for a miss."""
        logger.info(
            "[video] creator_comparison miss handle=%r reason=%s details=%s",
            creator_handle, reason, details,
        )
        if step_queue is not None:
            emit(step_queue, step_tool_complete(2, 0, 0, [], tool="creator_posts"))

    if not creator_handle:
        _miss("missing_creator_handle")
        return None
    if target_views <= 0:
        _miss("target_views_zero", target_views=target_views)
        return None

    handle_clean = creator_handle.lstrip("@").strip()
    if not handle_clean:
        _miss("empty_handle_after_clean", raw=creator_handle)
        return None

    emit(
        step_queue,
        step_tool_start(
            label=f"So sánh video của @{handle_clean}",
            iteration=2,
            index=0,
            tool="creator_posts",
        ),
    )
    posts: list[dict[str, Any]] = []
    try:
        posts = await fetch_user_posts(handle_clean, depth=1)
    except Exception as exc:
        logger.warning(
            "[video] creator_comparison miss handle=%r reason=ed_fetch_failed: %s",
            handle_clean, exc,
        )
        if step_queue is not None:
            emit(step_queue, step_tool_complete(2, 0, 0, [], tool="creator_posts"))
        return None

    posts = posts[:20]
    if len(posts) < 2:
        _miss("ed_returned_too_few_posts", returned=len(posts))
        return None

    target_vid = str(target_video_id or "")
    parsed: list[tuple[int, dict[str, Any]]] = []
    for p in posts:
        vid_id = str(p.get("aweme_id") or p.get("id") or "")
        if vid_id and vid_id == target_vid:
            continue
        stats = p.get("statistics") or p.get("stats") or {}
        v = int(stats.get("play_count") or stats.get("playCount") or 0)
        # 100-view floor matches the find_ab_pair guard from audit
        # Pass-2: flops with effectively-zero reach fabricate misleading
        # ``hit / flop`` deltas (5K / 0 = 5,000× would be rendered
        # as evidence to the user).
        if v >= 100:
            parsed.append((v, p))

    if len(parsed) < 2:
        zero_views_count = sum(
            1 for p in posts
            if int((p.get("statistics") or p.get("stats") or {})
                   .get("play_count") or 0) == 0
        )
        _miss(
            "too_few_posts_with_views",
            posts_returned=len(posts),
            posts_with_views=len(parsed),
            zero_view_posts=zero_views_count,
        )
        return None

    sorted_by_views = sorted(parsed, key=lambda x: x[0], reverse=True)
    all_views = [v for v, _ in sorted_by_views]

    hit_views, hit_post = sorted_by_views[0]
    flop_views, flop_post = sorted_by_views[-1]
    median_views = sorted(all_views)[len(all_views) // 2]

    # Same hit==flop guard: with only 1 post, hit_post == flop_post and
    # the comparison is meaningless. The < 2 gate should prevent this
    # but be defensive — render no card rather than a "1× delta" lie.
    if hit_views == flop_views or hit_post is flop_post:
        _miss("hit_equals_flop", parsed=len(parsed), hit_views=hit_views)
        return None

    delta = round(hit_views / max(flop_views, 1))
    target_ratio = target_views / max(median_views, 1)

    if target_ratio >= 5:
        percentile = "top 10% kênh"
    elif target_ratio >= 2:
        percentile = "trên mức trung bình"
    elif target_ratio >= 0.5:
        percentile = "dưới mức trung bình"
    else:
        percentile = "hiệu suất thấp nhất kênh"

    def _video_url(p: dict[str, Any]) -> str | None:
        vid = str(p.get("aweme_id") or p.get("id") or "")
        author = p.get("author") if isinstance(p.get("author"), dict) else {}
        handle = (
            author.get("unique_id")
            or author.get("uniqueId")
            or handle_clean
        )
        if isinstance(handle, str) and vid:
            return f"https://www.tiktok.com/@{handle.lstrip('@')}/video/{vid}"
        return None

    def _snippet(p: dict[str, Any]) -> str | None:
        d = str(p.get("desc") or p.get("caption") or "").strip()
        return d[:60] if d else None

    def _thumb(p: dict[str, Any]) -> str | None:
        video = p.get("video") if isinstance(p.get("video"), dict) else {}
        cover = video.get("cover") if isinstance(video.get("cover"), dict) else {}
        urls = cover.get("url_list") or []
        if urls and isinstance(urls[0], str):
            return urls[0]
        return None

    thumbs: list[str] = []
    for post in (hit_post, flop_post):
        t = _thumb(post)
        if t:
            thumbs.append(t)
            if len(thumbs) >= 2:
                break

    emit(
        step_queue,
        step_tool_complete(
            iteration=2,
            index=0,
            found=len(parsed),
            thumbnails=thumbs[:5],
            tool="creator_posts",
        ),
    )

    hid = str(hit_post.get("aweme_id") or hit_post.get("id") or "")
    fid = str(flop_post.get("aweme_id") or flop_post.get("id") or "")

    return CreatorComparison(
        creator_handle=f"@{handle_clean}",
        total_posts_analyzed=len(parsed),
        median_views=int(median_views),
        hit=CreatorComparisonVideo(
            video_id=hid or None,
            tiktok_url=_video_url(hit_post),
            views=hit_views,
            hook_type=_snippet(hit_post),
            thumbnail_url=_thumb(hit_post),
        ),
        flop=CreatorComparisonVideo(
            video_id=fid or None,
            tiktok_url=_video_url(flop_post),
            views=flop_views,
            hook_type=_snippet(flop_post),
            thumbnail_url=_thumb(flop_post),
        ),
        delta=delta,
        target_vs_median=round(target_ratio, 1),
        target_percentile=percentile,
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

    meta = out.get("meta") if isinstance(out.get("meta"), dict) else {}
    creator_handle = (
        str(meta.get("creator") or "").strip()
        or str(out.get("creator_handle") or "").strip()
    )
    target_views = int(meta.get("views") or 0)
    target_video_id = str(out.get("video_id") or "")

    if step_queue is not None:
        from getviews_pipeline.step_events import (
            emit,
            step_done,
            step_status,
            step_tool_complete,
            step_tool_start,
        )

        thumbs: list[str] = []
        tu = meta.get("thumbnail_url")
        if isinstance(tu, str) and tu.strip():
            thumbs.append(tu.strip())
        emit(step_queue, step_tool_complete(1, 0, 1, thumbs, tool="corpus"))
        if creator_handle and target_views > 0:
            emit(
                step_queue,
                step_status(2, "Đang so sánh với video khác của creator..."),
            )

    comparison: CreatorComparison | None = None
    if creator_handle and target_views > 0:
        try:
            _cmp_loop = asyncio.new_event_loop()
            # Must set as current thread's loop so that httpx AsyncClient inside
            # fetch_user_posts finds the correct loop via asyncio.get_event_loop().
            # Without this, httpx sees the old closed loop from a prior asyncio.run()
            # call (in run_video_analyze_pipeline) and raises "Event loop is closed".
            _prev_loop = asyncio.get_event_loop_policy().get_event_loop()
            asyncio.set_event_loop(_cmp_loop)
            try:
                comparison = _cmp_loop.run_until_complete(
                    build_creator_comparison(
                        creator_handle,
                        target_video_id,
                        target_views,
                        step_queue=step_queue,
                    )
                )
            finally:
                _cmp_loop.close()
                asyncio.set_event_loop(_prev_loop)
        except Exception as exc:
            logger.warning("[video] creator comparison failed: %s", exc)

    out["creator_comparison"] = (
        comparison.model_dump() if comparison is not None else None
    )

    # Live channel median: when CreatorComparison fetched ≥2 view-bearing
    # posts, use *that* median over the corpus-ingest snapshot. This is
    # what unblocks the "X.Y× kênh trung bình" tag on the on-demand path
    # (no corpus row → no `creator_median_views` column) and also keeps
    # corpus rows fresh against drift between ingest time and now.
    if comparison is not None:
        meta = out.get("meta") or {}
        live_median = int(comparison.median_views or 0)
        if live_median > 0:
            meta["creator_median_views"] = live_median
            target_views = int(meta.get("views") or 0)
            meta["target_vs_creator_median"] = (
                round(target_views / live_median, 2) if target_views else None
            )
            out["meta"] = meta

    if step_queue is not None:
        from getviews_pipeline.step_events import (
            emit,
            step_done,
            step_status,
            step_tool_start,
            step_tool_complete,
        )

        emit(
            step_queue,
            step_status(3, "Đang chạy Gemini phân tích frame..."),
        )
        emit(
            step_queue,
            step_tool_start("Phân tích 6 frame video", 3, 0, tool="synthesis"),
        )
        emit(step_queue, step_tool_complete(3, 0, 0, [], tool="synthesis"))
        emit(step_queue, step_done("Xong — đang hiển thị kết quả..."))

    return out
