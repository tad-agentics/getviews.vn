"""Layer 0A — Niche Insight Synthesis.

Runs weekly (Sunday) after sound_aggregator.
For each niche with sufficient corpus data, fetches the top-performing
hook+format formula, then uses contrastive framing (top 5 vs 5 baseline)
to extract causal mechanisms via Gemini.

Output stored in niche_insights table.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Minimum videos matching the top formula to run 0A for a niche.
# Below this threshold: skip — hallucinated insights are worse than no insights.
MIN_FORMULA_VIDEOS = 3
# Minimum baseline videos needed for contrastive framing.
MIN_BASELINE_VIDEOS = 3


@dataclass
class NicheInsightResult:
    insights_written: int = 0
    niches_skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _week_start_monday(today: date) -> date:
    return today - timedelta(days=today.weekday())


def _trim_for_layer0(analysis_json: dict, views: int, er: float) -> dict:
    """Extract mechanism-relevant fields only — reduces ~1500 tokens to ~400."""
    hook = (analysis_json.get("hook_analysis") or {})
    scenes = analysis_json.get("scenes") or []
    return {
        "hook_type": hook.get("hook_type"),
        "hook_phrase": hook.get("hook_phrase"),
        "face_appears_at": hook.get("face_appears_at"),
        "first_frame_type": hook.get("first_frame_type"),
        "text_overlays": (analysis_json.get("text_overlays") or [])[:3],
        "scene_sequence": [s.get("type") for s in scenes[:5]],
        "transitions_per_second": analysis_json.get("transitions_per_second"),
        "tone": analysis_json.get("tone"),
        "topics": analysis_json.get("topics"),
        "cta": analysis_json.get("cta"),
        "video_duration": scenes[-1].get("end") if scenes else None,
        "views": views,
        "er": round(er, 2),
    }


async def _fetch_top_formula(client: Any, niche_id: int, since_iso: str) -> dict | None:
    """Find the #1 hook+format combo by video count this week for a niche."""
    loop = asyncio.get_event_loop()

    def _query() -> list[dict]:
        return (
            client.table("video_corpus")
            .select("hook_type,content_format")
            .eq("niche_id", niche_id)
            .not_.is_("hook_type", None)
            .not_.is_("content_format", None)
            .gte("indexed_at", since_iso)
            .execute()
        ).data or []

    rows = await loop.run_in_executor(None, _query)
    if not rows:
        return None

    # Count combos
    counts: dict[tuple[str, str], int] = {}
    for r in rows:
        key = (r["hook_type"], r["content_format"])
        counts[key] = counts.get(key, 0) + 1

    best = max(counts, key=lambda k: counts[k])
    if counts[best] < MIN_FORMULA_VIDEOS:
        return None

    return {"hook_type": best[0], "content_format": best[1], "count": counts[best]}


async def _fetch_top_and_baseline(
    client: Any,
    niche_id: int,
    formula_hook: str,
    formula_format: str,
    since_iso: str,
) -> tuple[list[dict], list[dict]]:
    """Fetch trimmed top-5 and baseline-5 video dicts for contrastive framing."""
    loop = asyncio.get_event_loop()

    def _fetch_top() -> list[dict]:
        return (
            client.table("video_corpus")
            .select("video_id,analysis_json,views,likes,comments,shares")
            .eq("niche_id", niche_id)
            .eq("hook_type", formula_hook)
            .eq("content_format", formula_format)
            .gte("indexed_at", since_iso)
            .order("views", desc=True)
            .limit(5)
            .execute()
        ).data or []

    def _fetch_baseline() -> list[dict]:
        # Different hook+format combo from the top formula — average performers.
        # Excludes both hook_type AND content_format so the contrast is a genuinely
        # different combo, not just a hook variant of the same format.
        # Uses range(5, 9) within that filtered set to target mid-performers
        # (not viral outliers) for a clean causal signal.
        return (
            client.table("video_corpus")
            .select("video_id,analysis_json,views,likes,comments,shares")
            .eq("niche_id", niche_id)
            .not_.is_("hook_type", None)
            .not_.is_("content_format", None)
            .neq("hook_type", formula_hook)
            .neq("content_format", formula_format)
            .gte("indexed_at", since_iso)
            .order("views", desc=True)
            .range(5, 9)
            .execute()
        ).data or []

    top_raw, baseline_raw = await asyncio.gather(
        loop.run_in_executor(None, _fetch_top),
        loop.run_in_executor(None, _fetch_baseline),
    )

    def _trim_rows(rows: list[dict]) -> list[dict]:
        result = []
        for r in rows:
            views = int(r.get("views") or 0)
            likes = int(r.get("likes") or 0)
            comments = int(r.get("comments") or 0)
            shares = int(r.get("shares") or 0)
            er = (likes + comments + shares) / views if views > 0 else 0.0
            analysis = r.get("analysis_json") or {}
            if isinstance(analysis, str):
                try:
                    analysis = json.loads(analysis)
                except json.JSONDecodeError:
                    analysis = {}
            result.append(_trim_for_layer0(analysis, views, er))
        return result

    return _trim_rows(top_raw), _trim_rows(baseline_raw)


async def run_niche_insights(client: Any | None = None) -> NicheInsightResult:
    """Module 0A entry point. Called from _run_weekly_analytics in corpus_ingest.py."""
    from getviews_pipeline.supabase_client import get_service_client
    from getviews_pipeline.gemini import generate_niche_insight
    from getviews_pipeline.layer0_prompts import validate_niche_insight

    if client is None:
        client = get_service_client()

    result = NicheInsightResult()
    loop = asyncio.get_event_loop()

    week_of = _week_start_monday(date.today())
    week_of_str = week_of.isoformat()
    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    since_iso = since_dt.isoformat()
    computed_at = datetime.now(timezone.utc).isoformat()

    def _fetch_niches() -> list[dict]:
        return (
            client.table("niche_taxonomy")
            .select("id,name_vn,name_en")
            .execute()
        ).data or []

    niches = await loop.run_in_executor(None, _fetch_niches)
    if not niches:
        logger.warning("[layer0a] No niches found in niche_taxonomy")
        return result

    for niche in niches:
        niche_id = int(niche["id"])
        niche_name = niche.get("name_vn") or niche.get("name_en") or str(niche_id)

        try:
            formula = await _fetch_top_formula(client, niche_id, since_iso)
            if not formula:
                logger.info(
                    "[layer0a] niche=%s: insufficient data (<%d formula videos) — skipping",
                    niche_name, MIN_FORMULA_VIDEOS,
                )
                result.niches_skipped += 1
                continue

            top_videos, baseline_videos = await _fetch_top_and_baseline(
                client,
                niche_id,
                formula["hook_type"],
                formula["content_format"],
                since_iso,
            )

            if len(baseline_videos) < MIN_BASELINE_VIDEOS:
                logger.info(
                    "[layer0a] niche=%s: insufficient baseline videos (%d) — skipping",
                    niche_name, len(baseline_videos),
                )
                result.niches_skipped += 1
                continue

            # Call Gemini — blocking, run in executor
            insight_raw = await loop.run_in_executor(
                None,
                generate_niche_insight,
                niche_name,
                formula["hook_type"],
                formula["content_format"],
                top_videos,
                baseline_videos,
            )

            # Automated quality check
            quality = validate_niche_insight(insight_raw)
            quality_flag = None if quality["passed"] else "LOW"
            if quality_flag == "LOW":
                logger.warning(
                    "[layer0a] niche=%s: low quality insight — checks=%s",
                    niche_name, quality["checks"],
                )

            row = {
                "niche_id": niche_id,
                "week_of": week_of_str,
                "top_formula_hook": formula["hook_type"],
                "top_formula_format": formula["content_format"],
                "insight_text": insight_raw.get("insight_text"),
                "mechanisms": insight_raw.get("mechanisms"),
                "cross_niche_signals": None,  # filled by Module 0C separately
                "execution_tip": insight_raw.get("execution_tip"),
                "staleness_risk": insight_raw.get("staleness_risk"),
                "quality_flag": quality_flag,
                "computed_at": computed_at,
            }

            def _upsert(r: dict = row) -> None:
                client.table("niche_insights").upsert(
                    r, on_conflict="niche_id,week_of"
                ).execute()

            await loop.run_in_executor(None, _upsert)
            result.insights_written += 1
            logger.info(
                "[layer0a] niche=%s: insight written (quality=%s)",
                niche_name, quality_flag or "OK",
            )

        except Exception as exc:
            msg = f"niche={niche_name}: {exc}"
            logger.error("[layer0a] %s", msg)
            result.errors.append(msg)

    logger.info(
        "[layer0a] done: written=%d skipped=%d errors=%d",
        result.insights_written,
        result.niches_skipped,
        len(result.errors),
    )
    return result
