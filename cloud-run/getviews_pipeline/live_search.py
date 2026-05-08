"""
live_search.py — Query-time EnsembleData keyword search to supplement corpus.

Mirrors Lightreel's ``searchTikTokLive`` tool: targeted Vietnamese keyword
searches at synthesis time when the corpus sample is thin or the query has
recency signals ("đang viral", "tuần này", etc.).

Capped at MAX_LIVE_SEARCHES per call to stay inside ED Wood plan budget.
Only fires when ``needs_live_search`` is true (thin corpus or recency).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from getviews_pipeline.creator_blocklist import is_blocklisted_handle
from getviews_pipeline.ensemble import fetch_keyword_search
from getviews_pipeline.step_events import (
    emit,
    step_error,
    step_tool_complete,
    step_tool_start,
)

logger = logging.getLogger(__name__)

THIN_CORPUS_THRESHOLD = 50
MAX_LIVE_SEARCHES = 3

RECENCY_RE = re.compile(
    r"đang viral|tuần này|gần đây|mới nổi|hôm nay|trending|7 ngày|mới nhất",
    re.IGNORECASE,
)


def needs_live_search(query: str, corpus_count: int) -> bool:
    """Return True if live search should supplement corpus results."""
    return corpus_count < THIN_CORPUS_THRESHOLD or bool(RECENCY_RE.search(query or ""))


def derive_search_terms(
    niche_label: str,
    top_hook_types: list[str],
    query: str,
) -> list[str]:
    """Derive up to MAX_LIVE_SEARCHES Vietnamese TikTok search terms."""
    _ = query  # reserved for future query-aware expansion
    hook_map = {
        "bold_claim": "tuyên bố mạnh viral",
        "question": "câu hỏi hook tiktok",
        "before_after": "before after transformation",
        "story_open": "kể chuyện hook viral",
        "curiosity_gap": "tò mò bí ẩn tiktok",
        "social_proof": "bằng chứng xã hội viral",
        "shock_stat": "số liệu gây sốc tiktok",
        "how_to": "hướng dẫn tutorial viral",
        "pain_point": "nỗi đau giải pháp viral",
        "trend_hijack": "trend hijack tiktok viral",
    }
    terms: list[str] = []
    niche_vn = (niche_label or "tiktok").strip().lower()

    hooks_clean = [h.strip() for h in top_hook_types if h and str(h).strip()]
    for hook in hooks_clean[:2]:
        ht = hook.strip().lower().replace("-", "_")
        hook_phrase = hook_map.get(ht, hook.replace("_", " "))
        terms.append(f"{niche_vn} {hook_phrase}")

    terms.append(f"{niche_vn} tiktok viral tuần này")

    return terms[:MAX_LIVE_SEARCHES]


def format_live_awemes_for_prompt(awemes: list[dict[str, Any]]) -> str:
    """Format raw EnsembleData awemes as a compact prompt supplement."""
    if not awemes:
        return ""
    lines = ["\n\n## Video mới nhất từ TikTok (bổ sung live search, 7 ngày qua):"]
    for a in awemes[:15]:
        st = a.get("statistics") or a.get("stats") or {}
        views = int(st.get("play_count") or st.get("playCount") or 0)
        author = a.get("author") or {}
        handle = str(
            author.get("unique_id")
            or author.get("uniqueId")
            or author.get("nickname")
            or "unknown",
        )
        desc = str(a.get("desc") or a.get("caption") or "")[:80]
        lines.append(f"- @{handle} · {views:,} views · \"{desc}\"")
    lines.append(
        "(Các video trên là mẫu tìm kiếm real-time — dùng làm ngữ cảnh xu hướng; "
        "không bịa số liệu aggregate ngoài corpus.)",
    )
    return "\n".join(lines)


async def fetch_live_supplement(
    query: str,
    niche_label: str,
    top_hook_types: list[str],
    corpus_count: int,
    iteration_start: int = 2,
    *,
    step_queue: Any = None,
) -> list[dict[str, Any]]:
    """
    Fire up to MAX_LIVE_SEARCHES EnsembleData keyword searches and return
    merged aweme dicts (deduped by ``aweme_id``).

    Emits ``step_tool_start`` / ``step_tool_complete`` with ``tool=\"tiktok_live\"``.
    Returns [] on skip or failure — never raises.
    """
    if not needs_live_search(query, corpus_count):
        return []

    terms = derive_search_terms(niche_label, top_hook_types, query)
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # The terms list is bounded at MAX_LIVE_SEARCHES via derive_search_terms,
    # so all calls land at iteration_start. The earlier "i // MAX_LIVE_SEARCHES"
    # arithmetic was dead code (always 0) — kept the calc removed.
    for i, term in enumerate(terms):
        iteration = iteration_start
        index = i
        emit(
            step_queue,
            step_tool_start(
                label=f'Tìm kiếm TikTok: "{term}"',
                iteration=iteration,
                index=index,
                tool="tiktok_live",
            ),
        )

        awemes: list[dict[str, Any]] = []
        ed_failed = False
        try:
            awemes, _ = await fetch_keyword_search(
                term, period=7, sorting=1, country="vn"
            )
        except Exception as exc:
            ed_failed = True
            logger.warning("[live_search] ED keyword search failed term=%r: %s", term, exc)
            # Surface the failure as a step_error so the FE can flip the
            # "TikTok Live" card into an error state instead of showing
            # "0 video" — which reads as "search ran and found nothing"
            # rather than "search itself failed".
            emit(
                step_queue,
                step_error(
                    code="live_search_failed",
                    message_vi="Tìm kiếm TikTok live thất bại — kết quả pattern dùng corpus đã có.",
                    detail=f"term={term!r}: {exc}",
                ),
            )

        # Sprint 8.5 — apply the same news/aggregator blocklist the corpus
        # ingest enforces. Without this filter, EnsembleData live keyword
        # search returns theanh28*/kenh14*/24h.* / vtvcab.* etc. and feeds
        # them into the Gemini synthesis prompt for Pattern + Ideas,
        # silently undoing Sprint 8.5's value on the most prominent
        # surfaces. Re-uses ``is_blocklisted_handle`` from the corpus path.
        before = len(awemes)
        awemes = [
            a for a in awemes
            if not is_blocklisted_handle(
                str((a.get("author") or {}).get("unique_id") or "")
            )
        ]
        filtered = before - len(awemes)
        if filtered > 0:
            logger.info(
                "[live_search] term=%r filtered %d blocklisted aweme(s) (kept %d)",
                term, filtered, len(awemes),
            )

        thumbs: list[str] = []
        for a in awemes[:5]:
            video = a.get("video") if isinstance(a.get("video"), dict) else {}
            cover = video.get("cover") if isinstance(video.get("cover"), dict) else {}
            url_list = cover.get("url_list") or []
            url = url_list[0] if url_list else None
            if isinstance(url, str) and url:
                thumbs.append(url)

        # Skip the tool_complete emit when the ED call itself failed —
        # the step_error above already informs the FE; emitting a
        # complete with found=0 would double-up and look like a clean
        # "no results" outcome instead of an error.
        if not ed_failed:
            emit(
                step_queue,
                step_tool_complete(
                    iteration=iteration,
                    index=index,
                    found=len(awemes),
                    thumbnails=thumbs,
                    tool="tiktok_live",
                ),
            )

        for a in awemes:
            aid = str(a.get("aweme_id") or "")
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                results.append(a)

    return results
