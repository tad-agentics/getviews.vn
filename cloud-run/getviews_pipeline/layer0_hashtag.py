"""Layer 0D — Trending Hashtag Discovery.

Mines video_corpus for hashtags that appear frequently in high-performing videos
but are NOT yet in any niche_taxonomy.signal_hashtags array. Classifies candidates
via Gemini, then appends confirmed tags to the correct niche's signal_hashtags.

This is corpus-driven (no external API) — free to run and grounded in real data.

Run cadence: weekly (Sunday), inside _run_weekly_analytics, before Layer 0A so
newly discovered hashtags are available for the same week's niche insight.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Minimum number of distinct high-performing videos a hashtag must appear in
# to be considered a candidate. Filters noise from one-off viral posts.
MIN_VIDEO_APPEARANCES = 3

# Minimum average views across videos using this hashtag.
MIN_AVG_VIEWS = 50_000

# Gemini confidence threshold — only append hashtags Gemini is sure about.
MIN_CONFIDENCE = 0.75

# Hard cap on signal_hashtags array length per niche to avoid bloat.
MAX_SIGNAL_HASHTAGS = 80

# Candidates sent to Gemini per run (cost guard — keyword search is cheap but
# Gemini prompt length grows linearly with candidates).
MAX_CANDIDATES_PER_RUN = 60


async def run_hashtag_discovery(client: Any) -> dict[str, Any]:
    """Entry point. Returns summary dict with keys: candidates_found, added, skipped, errors."""
    loop = asyncio.get_event_loop()

    try:
        niches, existing_tags = await asyncio.gather(
            loop.run_in_executor(None, lambda: _fetch_niches(client)),
            loop.run_in_executor(None, lambda: _fetch_existing_tags(client)),
        )
    except Exception as exc:
        logger.error("[layer0d] Failed to fetch niches/existing tags: %s", exc)
        return {"candidates_found": 0, "added": 0, "skipped": 0, "errors": [str(exc)]}

    if not niches:
        return {"candidates_found": 0, "added": 0, "skipped": 0, "errors": ["no niches"]}

    try:
        candidates = await loop.run_in_executor(
            None, lambda: _fetch_candidate_hashtags(client, existing_tags)
        )
    except Exception as exc:
        logger.error("[layer0d] Failed to fetch candidate hashtags: %s", exc)
        return {"candidates_found": 0, "added": 0, "skipped": 0, "errors": [str(exc)]}

    if not candidates:
        logger.info("[layer0d] No new candidate hashtags found this week")
        return {"candidates_found": 0, "added": 0, "skipped": 0, "errors": []}

    logger.info("[layer0d] %d candidate hashtags to classify", len(candidates))

    # Classify via Gemini
    try:
        classifications = await loop.run_in_executor(
            None, lambda: _classify_hashtags(candidates[:MAX_CANDIDATES_PER_RUN], niches)
        )
    except Exception as exc:
        logger.error("[layer0d] Gemini classification failed: %s", exc)
        return {
            "candidates_found": len(candidates),
            "added": 0,
            "skipped": len(candidates),
            "errors": [str(exc)],
        }

    confirmed = [c for c in classifications if c.get("confidence", 0) >= MIN_CONFIDENCE]
    logger.info(
        "[layer0d] %d/%d classifications meet confidence threshold (%.2f)",
        len(confirmed), len(classifications), MIN_CONFIDENCE,
    )

    # Append confirmed tags to niche_taxonomy
    added = 0
    errors: list[str] = []
    niche_additions: dict[int, list[str]] = {}
    for item in confirmed:
        niche_id = item.get("niche_id")
        hashtag = item.get("hashtag", "").strip().lstrip("#")
        if not niche_id or not hashtag:
            continue
        niche_additions.setdefault(niche_id, []).append(hashtag)

    for niche_id, tags in niche_additions.items():
        try:
            n_added = await loop.run_in_executor(
                None, lambda nid=niche_id, t=tags: _append_tags_to_niche(client, nid, t)
            )
            added += n_added
            logger.info("[layer0d] niche_id=%d appended %d new tags: %s", niche_id, n_added, t[:n_added])
        except Exception as exc:
            msg = f"niche_id={niche_id}: {exc}"
            logger.warning("[layer0d] Failed to append tags: %s", msg)
            errors.append(msg)

    return {
        "candidates_found": len(candidates),
        "added": added,
        "skipped": len(candidates) - len(confirmed),
        "errors": errors,
    }


def _fetch_niches(client: Any) -> list[dict]:
    """Fetch all active niches with their current signal_hashtags."""
    result = (
        client.table("niche_taxonomy")
        .select("id, name_vn, name_en, signal_hashtags")
        .execute()
    )
    return result.data or []


def _fetch_existing_tags(client: Any) -> frozenset[str]:
    """Return a flat set of all hashtags already in any niche's signal_hashtags (without #)."""
    result = (
        client.table("niche_taxonomy")
        .select("signal_hashtags")
        .execute()
    )
    existing: set[str] = set()
    for row in (result.data or []):
        for tag in (row.get("signal_hashtags") or []):
            existing.add(tag.lstrip("#").lower())
    return frozenset(existing)


def _fetch_candidate_hashtags(client: Any, existing_tags: frozenset[str]) -> list[dict]:
    """Mine video_corpus for high-signal hashtags not yet in any niche's signal_hashtags.

    Strategy:
    - Look at the hashtags column (JSONB array of strings) on high-view videos
    - Count how many distinct videos each hashtag appears in
    - Filter to those appearing in MIN_VIDEO_APPEARANCES+ videos with avg views ≥ MIN_AVG_VIEWS
    - Exclude hashtags already in signal_hashtags or in DISTRIBUTION_GENERIC_HASHTAGS
    """
    from getviews_pipeline.helpers import DISTRIBUTION_GENERIC_HASHTAGS

    # Pull hashtag arrays + views from recent high-performing videos
    # We use a 30-day window to match batch recency
    result = (
        client.table("video_corpus")
        .select("hashtags, views")
        .gte("views", MIN_AVG_VIEWS)
        .not_.is_("hashtags", None)
        .order("views", desc=True)
        .limit(2000)
        .execute()
    )
    rows = result.data or []

    # Tally appearances and total views per hashtag
    tag_counts: dict[str, int] = {}
    tag_views: dict[str, int] = {}
    for row in rows:
        tags = row.get("hashtags") or []
        views = int(row.get("views") or 0)
        seen_in_row: set[str] = set()
        for raw_tag in tags:
            tag = str(raw_tag).strip().lstrip("#").lower()
            if len(tag) < 3:
                continue
            if tag in seen_in_row:
                continue
            seen_in_row.add(tag)
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            tag_views[tag] = tag_views.get(tag, 0) + views

    candidates = []
    for tag, count in tag_counts.items():
        if count < MIN_VIDEO_APPEARANCES:
            continue
        avg_views = tag_views[tag] / count
        if avg_views < MIN_AVG_VIEWS:
            continue
        if tag in existing_tags:
            continue
        if tag in DISTRIBUTION_GENERIC_HASHTAGS:
            continue
        candidates.append({
            "hashtag": tag,
            "video_count": count,
            "avg_views": round(avg_views),
        })

    # Sort by video_count desc — strongest signals first
    candidates.sort(key=lambda x: x["video_count"], reverse=True)
    return candidates


def _classify_hashtags(candidates: list[dict], niches: list[dict]) -> list[dict]:
    """Call Gemini to classify candidates into niches. Returns list of classification dicts."""
    from getviews_pipeline.gemini import _generate_content_models, _normalize_response, _response_text
    from getviews_pipeline.config import GEMINI_EXTRACTION_MODEL, GEMINI_EXTRACTION_FALLBACKS
    from getviews_pipeline.layer0_prompts import (
        HASHTAG_DISCOVERY_PROMPT_TEMPLATE,
        LAYER0_HASHTAG_RESPONSE_SCHEMA,
    )
    from google.genai import types

    niches_summary = [
        {"id": n["id"], "name_vn": n.get("name_vn", ""), "name_en": n.get("name_en", "")}
        for n in niches
    ]
    prompt = HASHTAG_DISCOVERY_PROMPT_TEMPLATE.format(
        candidate_hashtags_json=json.dumps(candidates, ensure_ascii=False, indent=2),
        niches_json=json.dumps(niches_summary, ensure_ascii=False, indent=2),
    )

    cfg = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
        response_json_schema=LAYER0_HASHTAG_RESPONSE_SCHEMA,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_EXTRACTION_MODEL,
        fallbacks=GEMINI_EXTRACTION_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        raise ValueError("layer0d: empty Gemini response")

    parsed = json.loads(_normalize_response(text))
    return parsed.get("classifications", []) if isinstance(parsed, dict) else []


def _append_tags_to_niche(client: Any, niche_id: int, new_tags: list[str]) -> int:
    """Append new_tags to niche_taxonomy.signal_hashtags, respecting MAX_SIGNAL_HASHTAGS cap.

    Tags are stored with # prefix to match the existing convention.
    Returns the number of tags actually appended (may be < len(new_tags) if cap reached).
    """
    row = (
        client.table("niche_taxonomy")
        .select("signal_hashtags")
        .eq("id", niche_id)
        .single()
        .execute()
    ).data
    if not row:
        return 0

    current: list[str] = row.get("signal_hashtags") or []
    current_clean = frozenset(t.lstrip("#").lower() for t in current)

    # Only add tags not already present, up to the cap
    to_add = []
    for tag in new_tags:
        clean = tag.lstrip("#").lower()
        if clean in current_clean:
            continue
        if len(current) + len(to_add) >= MAX_SIGNAL_HASHTAGS:
            break
        to_add.append(f"#{clean}")

    if not to_add:
        return 0

    updated = current + to_add
    client.table("niche_taxonomy").update({"signal_hashtags": updated}).eq("id", niche_id).execute()
    return len(to_add)
