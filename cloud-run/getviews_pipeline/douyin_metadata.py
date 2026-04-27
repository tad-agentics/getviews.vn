"""D2b (2026-06-03) — Kho Douyin · metadata parser + corpus row builder.

Pure functions only — no network, no DB writes, no Gemini calls. The
D2c ingest orchestrator wires these together with EnsembleData fetches
+ ``analyze_aweme`` + ``translate_douyin_caption`` + the upsert path.

What this module owns:

  • ``build_douyin_url(aweme_id)`` — canonical
    ``https://www.douyin.com/video/<aweme_id>`` URL.
  • ``parse_douyin_metadata(aweme)`` — re-exports the TikTok
    ``parse_metadata`` (Douyin awemes share the schema per ED docs).
    Kept as a separate symbol so the ingest pipeline reads as
    "Douyin parser" not "TikTok parser borrowed for Douyin" — clearer
    blame when behaviours diverge in future.
  • ``build_douyin_corpus_row(aweme, analysis, niche_id, translation?)``
    → row dict matching ``douyin_video_corpus`` columns. Returns
    ``None`` when the analysis errored (caller skips the video).

Shape of the returned row mirrors ``douyin_video_corpus`` schema from
``20260603000001_douyin_video_corpus.sql``:

  Identity / metrics filled in this PR (D2b):
    video_id, douyin_url, content_type, niche_id, creator_handle,
    creator_name, creator_followers, thumbnail_url, video_url,
    frame_urls, analysis_json, views, likes, comments, shares, saves,
    engagement_rate, posted_at, video_duration, hook_type, hook_phrase,
    title_zh, title_vi, sub_vi, hashtags_zh

  Filled by D3 synth (NULL on the row this PR emits):
    sub_vi (D3 may overwrite the translator's gloss), adapt_level,
    adapt_reason, eta_weeks_min, eta_weeks_max, cn_rise_pct,
    translator_notes, synth_computed_at

The row builder INTENTIONALLY does NOT include Vietnamese-specific
classifiers (``_classify_cta``, ``_detect_dialect``, ``_detect_commerce``
from ``corpus_ingest.py``) — those are VN-keyword-based and don't apply
to Chinese transcripts. ``content_format`` is also skipped here; if a
Douyin-shaped format classifier becomes useful, it lands as a
follow-up.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.douyin_translator import CaptionTranslation
from getviews_pipeline.ensemble import VideoMetadata, parse_metadata

logger = logging.getLogger(__name__)


# ── Public re-export so callers don't have to know about ensemble.py ──


def parse_douyin_metadata(aweme: dict[str, Any]) -> VideoMetadata:
    """Parse a Douyin aweme into ``VideoMetadata``.

    EnsembleData normalises Douyin and TikTok awemes into the same
    schema, so we delegate to the existing TikTok parser. Kept as a
    distinct symbol so call sites read intent-first; if Douyin's
    schema diverges in future, this is the one place to special-case.
    """
    return parse_metadata(aweme)


def build_douyin_url(aweme_id: str) -> str:
    """Canonical Douyin web URL. ``https://www.douyin.com/video/<id>``.

    Used by the FE Kho Douyin surface as the click-out link on every
    video card. Strips any whitespace; the ingest pipeline guarantees
    a non-empty ``aweme_id`` upstream so we don't need to defend
    against empty input here, but trim defensively to keep the
    boundary clean.
    """
    return f"https://www.douyin.com/video/{(aweme_id or '').strip()}"


# ── Helpers ─────────────────────────────────────────────────────────


_HANDLE_NOISE_RE = re.compile(r"\s+")


def _normalize_handle(raw: str | None) -> str:
    """Mirror of corpus_ingest._normalize_handle but kept local so the
    Douyin module doesn't import from corpus_ingest (avoids circular
    import once D2c's ``douyin_ingest`` lands)."""
    if not raw:
        return "unknown"
    return _HANDLE_NOISE_RE.sub("", raw.lstrip("@").lower())


def _safe_engagement_rate(
    *,
    er_from_analysis: float | int | None,
    views: int,
    likes: int,
    comments: int,
    shares: int,
    saves: int,
) -> float:
    """Engagement rate with Douyin's save signal included.

    Mirrors ``corpus_ingest._safe_engagement_rate`` but adds ``saves``
    to the numerator — Douyin emphasises save+share strongly (algorithm
    signal for re-watch / collection). Capped at 100.0.
    """
    if er_from_analysis is not None:
        try:
            v = float(er_from_analysis)
            if v > 0:
                return min(v, 100.0)
        except (TypeError, ValueError):
            pass
    if views <= 0:
        return 0.0
    return min((likes + comments + shares + saves) / views * 100.0, 100.0)


# ── Row builder ─────────────────────────────────────────────────────


def build_douyin_corpus_row(
    aweme: dict[str, Any],
    analysis: dict[str, Any],
    niche_id: int,
    *,
    translation: CaptionTranslation | None = None,
) -> dict[str, Any] | None:
    """Map ``aweme + analysis [+ translation]`` → ``douyin_video_corpus``
    row dict ready for upsert.

    Returns ``None`` on:
      • Analysis errored (no ``analysis`` key in the dict).
      • Empty ``aweme_id`` (can't dedupe; should never happen but defensive).

    ``translation`` is optional — when omitted (translator failed or
    skipped), ``title_vi`` / ``sub_vi`` land as ``None`` and D3 synth
    re-attempts on the stale row. ``title_zh`` is always populated
    from the raw aweme ``desc`` so the modal can show the Chinese
    caption even before translation lands.
    """
    if "error" in analysis or "analysis" not in analysis:
        return None

    video_id = str(aweme.get("aweme_id", "") or "")
    if not video_id:
        return None

    # ── Author + URLs ────────────────────────────────────────────
    raw_author: dict[str, Any] = aweme.get("author") or {}
    handle = _normalize_handle(
        str(raw_author.get("unique_id", "") or "") or None
    )
    creator_name = str(raw_author.get("nickname", "") or "") or None
    creator_followers_raw = (
        raw_author.get("follower_count")
        or raw_author.get("followerCount")
    )
    creator_followers = (
        int(creator_followers_raw) if creator_followers_raw is not None else None
    )

    douyin_url = build_douyin_url(video_id)

    video_obj: dict[str, Any] = aweme.get("video") or {}
    cover = video_obj.get("origin_cover") or video_obj.get("cover") or {}
    cover_urls: list[str] = cover.get("url_list") or []
    thumbnail_url: str | None = cover_urls[0] if cover_urls else None

    video_urls = ensemble.extract_video_urls(aweme)
    video_url = video_urls[0] if video_urls else None

    # ── Engagement ───────────────────────────────────────────────
    raw_stats: dict[str, Any] = aweme.get("statistics") or {}
    metadata = analysis.get("metadata") or {}
    metrics = metadata.get("metrics") or {}

    views = int(metrics.get("views") or raw_stats.get("play_count") or 0)
    likes = int(metrics.get("likes") or raw_stats.get("digg_count") or 0)
    comments = int(metrics.get("comments") or raw_stats.get("comment_count") or 0)
    shares = int(metrics.get("shares") or raw_stats.get("share_count") or 0)
    saves = int(metrics.get("bookmarks") or raw_stats.get("collect_count") or 0)
    engagement_rate = _safe_engagement_rate(
        er_from_analysis=analysis.get("engagement_rate") or metadata.get("engagement_rate"),
        views=views,
        likes=likes,
        comments=comments,
        shares=shares,
        saves=saves,
    )

    # ── Posting time + duration ──────────────────────────────────
    create_time: int | None = aweme.get("create_time") or aweme.get("createTime")
    posted_at: str | None = (
        datetime.fromtimestamp(int(create_time), tz=UTC).isoformat()
        if create_time
        else None
    )

    analysis_json: dict[str, Any] = analysis.get("analysis") or {}
    scenes: list[dict[str, Any]] = analysis_json.get("scenes") or []
    video_duration = float(scenes[-1]["end"]) if scenes and scenes[-1].get("end") is not None else None

    # ── Hook (Gemini analysis) ───────────────────────────────────
    hook_info: dict[str, Any] = analysis_json.get("hook_analysis") or {}
    hook_type = (hook_info.get("hook_type") or "").strip().lower() or None
    hook_phrase = hook_info.get("hook_phrase") or None

    # ── Caption + Chinese hashtags ───────────────────────────────
    title_zh = str(aweme.get("desc", "") or "") or None
    hashtags_zh: list[str] = []
    for item in aweme.get("text_extra") or []:
        if isinstance(item, dict) and item.get("hashtag_name"):
            hashtags_zh.append(f"#{item['hashtag_name']}")

    # ── Translation (optional) ───────────────────────────────────
    title_vi: str | None = None
    sub_vi: str | None = None
    if translation is not None:
        title_vi = translation.title_vi
        sub_vi = translation.sub_vi

    # Detect content_type for Douyin (carousel vs video) — same logic
    # as TikTok ingest because EnsembleData normalises the field name.
    content_type = ensemble.detect_content_type(aweme)

    return {
        # ── Identity / FK ────────────────────────────────────────
        "video_id": video_id,
        "douyin_url": douyin_url,
        "content_type": content_type,
        "niche_id": niche_id,
        # ── Creator ──────────────────────────────────────────────
        "creator_handle": handle,
        "creator_name": creator_name,
        "creator_followers": creator_followers,
        # ── Media ────────────────────────────────────────────────
        "thumbnail_url": thumbnail_url,
        "video_url": video_url,
        "frame_urls": [],  # D2c fills via R2 extraction
        "analysis_json": analysis_json,
        # ── Metrics ──────────────────────────────────────────────
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "engagement_rate": engagement_rate,
        # ── Posting + duration ───────────────────────────────────
        "posted_at": posted_at,
        "video_duration": video_duration,
        # ── Hook (Gemini) ────────────────────────────────────────
        "hook_type": hook_type,
        "hook_phrase": hook_phrase,
        # ── Caption + translation ────────────────────────────────
        "title_zh": title_zh,
        "title_vi": title_vi,
        "sub_vi": sub_vi,
        "hashtags_zh": hashtags_zh,
        # D3 synth fields stay NULL — the schema's CHECK on
        # ``adapt_level`` tolerates NULL and the FE renders a
        # "human review pending" caveat below the chip.
    }
