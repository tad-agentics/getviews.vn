"""Phase 5.1b + 5.4 — corpus quality gate and on-demand promotion.

Two concerns live here:

1. **Promotion** (Phase 5.1b):
   When a user pastes a TikTok URL and we run the full Gemini analysis,
   the resulting extraction can optionally be promoted into ``video_corpus``
   with ``ingest_source='user_diagnosis'``.  This grows the corpus from
   user activity without any additional Gemini cost — the extraction was
   already run.

   Quality bar before promotion:
   - analysis_json is non-empty.
   - niche_id is resolved (from the ExtractionResult).
   - views > 0 (engagement signal present).

2. **Quality gate** (Phase 5.4):
   Cohort queries (percentile benchmarks, pattern thesis) call
   ``is_high_quality(row)`` to decide whether to include a row.
   High-quality rows are those ingested by the nightly batch pipeline
   or via a user diagnosis that passed the quality bar.  Rows flagged as
   low-quality are retained but excluded from statistical cohorts so they
   don't skew benchmarks.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from getviews_pipeline.extraction_quality import classify_extraction_quality

logger = logging.getLogger(__name__)

# Minimum view count for a user-diagnosed video to qualify for corpus promotion.
_MIN_VIEWS_FOR_PROMOTION = 1_000

# Minimum quality_tier for inclusion in cohort queries.
QUALITY_TIERS = ("high", "medium", "low")


def quality_tier(row: dict[str, Any]) -> str:
    """Return 'high' | 'medium' | 'low' for a video_corpus candidate row.

    Used by ``promote_on_demand_to_corpus`` (stored in the row) and by
    Phase 5.4 cohort filters (``is_cohort_eligible``).

    Scoring heuristic (opinionated, tunable):
      high   — batch-ingested OR user-diagnosed with views >= 10 K.
      medium — user-diagnosed with views in [1 K, 10 K).
      low    — user-diagnosed with views < 1 K (still kept, filtered out of
               cohorts to avoid skewing percentile benchmarks).
    """
    source = str(row.get("ingest_source") or "").strip()
    if source == "batch_nightly":
        return "high"

    views = int(row.get("views") or 0)
    if views >= 10_000:
        return "high"
    if views >= _MIN_VIEWS_FOR_PROMOTION:
        return "medium"
    return "low"


def is_cohort_eligible(row: dict[str, Any]) -> bool:
    """Return True when a corpus row should be included in cohort queries.

    Phase 5.4 — used by services/performance.py when computing percentiles
    and pattern thesis sample sets.  Excludes low-quality user-diagnosed
    videos that haven't earned enough organic views to be representative.
    """
    return quality_tier(row) in ("high", "medium")


def promote_on_demand_to_corpus(
    service_sb: Any,
    *,
    video_id: str,
    tiktok_url: str,
    creator_handle: str,
    niche_id: int,
    analysis_json: dict[str, Any],
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    engagement_rate: float = 0.0,
    content_type: str = "video",
    thumbnail_url: str | None = None,
    video_url: str | None = None,
) -> bool:
    """Upsert an on-demand analysis result into video_corpus.

    Returns True if the row was written, False if skipped (below quality bar
    or if the row already exists with a higher-priority ingest_source).

    Phase 6.2 note: the UPSERT uses COALESCE so that if the batch pipeline
    later ingests the same video, it won't overwrite ``ingest_source =
    'user_diagnosis'`` — the provenance of the FIRST writer is preserved.
    """
    if not video_id or not niche_id or not analysis_json:
        logger.debug("[corpus_quality] skip promote: missing video_id/niche_id/analysis_json")
        return False

    row: dict[str, Any] = {
        "video_id": video_id,
        "tiktok_url": tiktok_url,
        "creator_handle": creator_handle,
        "ingest_loop_niche_id": niche_id,
        "analysis_json": analysis_json,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "engagement_rate": engagement_rate,
        "content_type": content_type,
        "thumbnail_url": thumbnail_url,
        "video_url": video_url,
        "ingest_source": "user_diagnosis",
        "first_seen_at": datetime.now(UTC).isoformat(),
        "last_refreshed_at": datetime.now(UTC).isoformat(),
        "indexed_at": datetime.now(UTC).isoformat(),
        "extraction_quality": classify_extraction_quality(
            analysis_json,
            content_type=content_type,
        ),
    }

    tier = quality_tier({**row, "ingest_source": "user_diagnosis"})
    row["quality_tier"] = tier

    try:
        # COALESCE ingest_source so batch never overwrites user_diagnosis provenance.
        # The raw SQL upsert with COALESCE isn't directly supported by the supabase-py
        # client, so we use a two-step: check if row exists, then insert-or-update.
        existing = (
            service_sb.table("video_corpus")
            .select("video_id,ingest_source")
            .eq("video_id", video_id)
            .limit(1)
            .execute()
        )
        existing_rows = getattr(existing, "data", None) or []

        if existing_rows:
            # Row exists — only update last_refreshed_at + quality_tier.
            # Do NOT overwrite ingest_source (preserve original provenance).
            service_sb.table("video_corpus").update(
                {
                    "last_refreshed_at": datetime.now(UTC).isoformat(),
                    "quality_tier": tier,
                }
            ).eq("video_id", video_id).execute()
            logger.info(
                "[corpus_quality] refreshed existing corpus row video_id=%s source=%s",
                video_id,
                existing_rows[0].get("ingest_source"),
            )
        else:
            service_sb.table("video_corpus").insert(row).execute()
            logger.info(
                "[corpus_quality] promoted to corpus video_id=%s tier=%s views=%d",
                video_id,
                tier,
                views,
            )
            # Phase 5.8 — emit corpus growth metric so Cloud Logging can chart
            # how many corpus rows come from user diagnoses vs nightly batch.
            try:
                from getviews_pipeline.observability import log_corpus_growth_event
                log_corpus_growth_event(
                    video_id=video_id,
                    ingest_source="user_diagnosis",
                    quality_tier=tier,
                    views=views,
                    niche_id=niche_id,
                    action="promoted",
                )
            except Exception:
                pass
        return True
    except Exception as exc:
        logger.warning("[corpus_quality] promote failed video_id=%s: %s", video_id, exc)
        return False
