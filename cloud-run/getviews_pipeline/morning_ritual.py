"""Morning Ritual generator — 3 ready-to-shoot TikTok scripts per creator per day.

The design's hero feature: every morning, a creator opens the app and sees
three distinct script kernels grounded in what's moving in their niche this
week. This module produces those kernels.

Pipeline:
  1. Resolve the user's niche + reference_channel_handles.
  2. Build a grounding pool of 10–20 top-performing videos. Prefer the
     user's reference channels (last 7d); fall back to the niche's top
     videos last 7d; fall back again to last 30d. Carry the claim_tiers
     tier forward as `adequacy` so the UI can soften retention claims.
  3. Ask Gemini for 3 distinct RitualScript objects, each using a different
     hook type from the canonical 15-name taxonomy. Schema-enforced via
     pydantic + response_json_schema.
  4. Upsert into daily_ritual keyed by (user_id, today_utc, niche_id).

Intentionally sync + single-user per call — the batch job iterates in the
orchestrator. Makes it trivial to retry/debug one user without touching the
batch loop.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from getviews_pipeline.claim_tiers import CLAIM_TIERS, flags_for_count
from getviews_pipeline.output_redesign import HOOK_TYPE_VI

logger = logging.getLogger(__name__)


# ── Canonical hook-type enum (matches HOOK_TYPE_VI keys) ──────────────────
# Gemini must pick one of these 15 literals; we derive the Vietnamese
# display name post-hoc so the model can't drift from the fixed taxonomy.
HookTypeEn = Literal[
    "warning", "price_shock", "shock_stat", "reaction", "comparison",
    "expose", "controversy", "how_to", "story_open", "pov",
    "social_proof", "curiosity_gap", "bold_claim", "challenge",
    "question", "pain_point", "trend_hijack", "insider", "secret",
]


class RitualScript(BaseModel):
    """One of three ready-to-shoot script kernels.

    Fields map 1:1 to what the design's MorningRitual card renders:
    hook-type badge, quoted title line, why-it-works caption, retention %,
    shot count, length in seconds.
    """

    hook_type_en: HookTypeEn = Field(
        description="Canonical hook-type enum. Pick one from the allowed list.",
    )
    title_vi: str = Field(
        min_length=8, max_length=90,
        description="Câu hook thật sự người quay có thể đọc. "
                    "Không mô tả — viết trực tiếp, đặt trong \"dấu ngoặc kép\".",
    )
    why_works: str = Field(
        min_length=20, max_length=140,
        description="1 câu Vietnamese giải thích cơ chế psychology đằng sau hook.",
    )
    retention_est_pct: int = Field(
        ge=30, le=90,
        description="Ước lượng retention % realistic dựa trên dữ liệu grounding.",
    )
    shot_count: int = Field(
        ge=2, le=8,
        description="Số shot / scene. Realistic cho TikTok ngắn.",
    )
    length_sec: int = Field(
        ge=15, le=90,
        description="Độ dài video tính bằng giây.",
    )


class RitualBundle(BaseModel):
    """Exactly 3 distinct scripts, each with a different hook_type_en."""

    scripts: list[RitualScript] = Field(min_length=3, max_length=3)


@dataclass(frozen=True)
class RitualResult:
    """What the batch job upserts to daily_ritual for one user."""

    user_id: str
    niche_id: int
    scripts: list[dict[str, Any]]     # each item = RitualScript.model_dump() + hook_type_vi
    adequacy: str                      # claim_tiers tier of the grounding slice
    grounded_video_ids: list[str]
    generated_for_date: date
    error: str | None = None           # set when Gemini fails — caller logs, skips write


MIN_GROUNDING_VIDEOS = 10
TARGET_GROUNDING_VIDEOS = 20


# ── Grounding ──────────────────────────────────────────────────────────────


def _fetch_grounding_videos(
    client: Any,
    niche_id: int,
    reference_handles: list[str],
) -> tuple[list[dict[str, Any]], str]:
    """Build the video pool + adequacy tier for a user.

    Priority:
      1. reference_handles set → last-7d in niche where creator_handle ∈ handles
      2. else last-7d top by views in niche
      3. if still < MIN_GROUNDING_VIDEOS → last-30d top by views in niche

    Returns (videos, adequacy). `videos` is empty when no source yields a
    usable pool; the caller then returns a 'thin' RitualResult.
    """
    now = datetime.now(timezone.utc)
    since_7d = (now - timedelta(days=7)).isoformat()
    since_30d = (now - timedelta(days=30)).isoformat()

    pool: list[dict[str, Any]] = []

    # Step 1 — reference-anchored, 7d.
    if reference_handles:
        try:
            rows = (
                client.table("video_corpus")
                .select("video_id, creator_handle, views, analysis_json, thumbnail_url, hook_phrase, hook_type")
                .eq("niche_id", niche_id)
                .in_("creator_handle", reference_handles)
                .gte("created_at", since_7d)
                .order("views", desc=True)
                .limit(TARGET_GROUNDING_VIDEOS)
                .execute()
                .data or []
            )
            pool = list(rows)
        except Exception as exc:
            logger.warning("[ritual] ref-anchored fetch failed: %s", exc)

    # Step 2 — niche-wide, 7d.
    if len(pool) < MIN_GROUNDING_VIDEOS:
        try:
            rows = (
                client.table("video_corpus")
                .select("video_id, creator_handle, views, analysis_json, thumbnail_url, hook_phrase, hook_type")
                .eq("niche_id", niche_id)
                .gte("created_at", since_7d)
                .order("views", desc=True)
                .limit(TARGET_GROUNDING_VIDEOS)
                .execute()
                .data or []
            )
            seen = {v["video_id"] for v in pool}
            pool = pool + [r for r in rows if r.get("video_id") not in seen]
        except Exception as exc:
            logger.warning("[ritual] niche-wide 7d fetch failed: %s", exc)

    # Step 3 — niche-wide, 30d (last resort).
    if len(pool) < MIN_GROUNDING_VIDEOS:
        try:
            rows = (
                client.table("video_corpus")
                .select("video_id, creator_handle, views, analysis_json, thumbnail_url, hook_phrase, hook_type")
                .eq("niche_id", niche_id)
                .gte("created_at", since_30d)
                .order("views", desc=True)
                .limit(TARGET_GROUNDING_VIDEOS)
                .execute()
                .data or []
            )
            seen = {v["video_id"] for v in pool}
            pool = pool + [r for r in rows if r.get("video_id") not in seen]
        except Exception as exc:
            logger.warning("[ritual] niche-wide 30d fetch failed: %s", exc)

    # Cap the pool and stamp adequacy off the pool size (not the 30d count —
    # this reflects how confident the grounding actually is).
    pool = pool[:TARGET_GROUNDING_VIDEOS]
    adequacy = flags_for_count(len(pool)).highest_passing_tier
    return pool, adequacy


# ── Prompt ─────────────────────────────────────────────────────────────────


_PROMPT_TEMPLATE = """Bạn là content strategist cho TikTok creator trong ngách **{niche_name}**.

Hãy tạo 3 kịch bản video ĐỘC LẬP, mỗi cái dùng **một hook_type_en khác nhau** (không trùng).

Grounding (20 video nổi bật trong ngách tuần này):
{grounding_json}

Yêu cầu cho mỗi kịch bản:
- hook_type_en: pick 1 trong danh sách literal schema cho phép.
- title_vi: câu hook creator đọc trực tiếp vào camera, đặt trong "dấu ngoặc kép". ≤ 90 ký tự. KHÔNG mô tả ("video về…"), viết thành câu.
- why_works: 1 câu Vietnamese, ≤ 140 ký tự. Giải thích cơ chế psychology, KHÔNG hứa hẹn "viral".
- retention_est_pct: realistic 40-75% dựa trên grounding. Đừng cường điệu.
- shot_count + length_sec: realistic cho TikTok ngắn (3-6 shot, 20-45 giây là sweet spot).

QUY TẮC:
- Title phải ngắn, punchy, tiếng Việt tự nhiên — không dịch Anh-Việt cứng.
- KHÔNG lặp lại y nguyên hook của video trong grounding — chắt lọc pattern, không copy-paste.
- 3 kịch bản phải ĐA DẠNG hook_type (VD: pov + shock_stat + story_open, không phải 3 pov).
- TRÁNH TUYỆT ĐỐI các cụm sáo rỗng: "tính năng ẩn", "bí mật không ai nói", "sự thật shock", "chỉ 1%", "hack não", "đừng bỏ qua", "xem ngay kẻo muộn". Thay bằng chi tiết cụ thể từ ngách.
{reference_note}"""


def _build_prompt(
    niche_name: str,
    videos: list[dict[str, Any]],
    reference_handles: list[str],
) -> str:
    # Trim the grounding payload so the prompt doesn't balloon — Gemini
    # only needs hook + hook_type + views per row to pattern-match.
    trimmed = [
        {
            "video_id": v.get("video_id"),
            "creator": v.get("creator_handle"),
            "views":   v.get("views"),
            "hook_type": v.get("hook_type"),
            "hook_phrase": v.get("hook_phrase"),
        }
        for v in videos
    ]
    reference_note = ""
    if reference_handles:
        handles_fmt = ", ".join(f"@{h}" for h in reference_handles[:3])
        reference_note = (
            f"\n- Ưu tiên giọng + phong cách giống các kênh tham chiếu của creator: {handles_fmt}."
        )
    return _PROMPT_TEMPLATE.format(
        niche_name=niche_name,
        grounding_json=json.dumps(trimmed, ensure_ascii=False, indent=2),
        reference_note=reference_note,
    )


# ── Main entry ─────────────────────────────────────────────────────────────


def generate_ritual_for_user(
    client: Any,
    *,
    user_id: str,
    niche_id: int,
    niche_name: str,
    reference_handles: list[str],
    for_date: date | None = None,
) -> RitualResult:
    """Generate today's 3 scripts for one user. Sync — called from the batch loop."""
    from getviews_pipeline.gemini import _generate_content_models, _response_text, _normalize_response
    from getviews_pipeline.config import (
        GEMINI_SYNTHESIS_MODEL, GEMINI_SYNTHESIS_FALLBACKS,
    )
    from google.genai import types  # type: ignore[import-untyped]

    target_date = for_date or datetime.now(timezone.utc).date()

    videos, adequacy = _fetch_grounding_videos(client, niche_id, reference_handles)
    if len(videos) < MIN_GROUNDING_VIDEOS:
        return RitualResult(
            user_id=user_id,
            niche_id=niche_id,
            scripts=[],
            adequacy=adequacy,
            grounded_video_ids=[v.get("video_id", "") for v in videos],
            generated_for_date=target_date,
            error=f"thin_corpus: only {len(videos)} grounding videos",
        )

    prompt = _build_prompt(niche_name, videos, reference_handles)
    config = types.GenerateContentConfig(
        temperature=0.6,   # distinct scripts need some creativity
        response_mime_type="application/json",
        response_json_schema=RitualBundle.model_json_schema(),
    )

    try:
        response = _generate_content_models(
            [prompt],
            primary_model=GEMINI_SYNTHESIS_MODEL,
            fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
            config=config,
        )
    except Exception as exc:
        logger.exception("[ritual] Gemini call failed user=%s: %s", user_id, exc)
        return RitualResult(
            user_id=user_id, niche_id=niche_id, scripts=[],
            adequacy=adequacy,
            grounded_video_ids=[v.get("video_id", "") for v in videos],
            generated_for_date=target_date,
            error=f"gemini_error: {exc}",
        )

    raw = _response_text(response)
    try:
        bundle = RitualBundle.model_validate_json(_normalize_response(raw))
    except Exception as exc:
        logger.warning(
            "[ritual] schema validation failed user=%s: %s (raw=%r)",
            user_id, exc, raw[:400],
        )
        return RitualResult(
            user_id=user_id, niche_id=niche_id, scripts=[],
            adequacy=adequacy,
            grounded_video_ids=[v.get("video_id", "") for v in videos],
            generated_for_date=target_date,
            error=f"schema_error: {exc}",
        )

    # Enrich with Vietnamese display name, dedupe hook types defensively.
    scripts_out: list[dict[str, Any]] = []
    seen_hooks: set[str] = set()
    for s in bundle.scripts:
        if s.hook_type_en in seen_hooks:
            continue
        seen_hooks.add(s.hook_type_en)
        item = s.model_dump()
        item["hook_type_vi"] = HOOK_TYPE_VI.get(s.hook_type_en, s.hook_type_en)
        scripts_out.append(item)

    if len(scripts_out) < 3:
        # Gemini duplicated hook types — treat as soft failure, caller can
        # retry tomorrow rather than writing a degraded row.
        return RitualResult(
            user_id=user_id, niche_id=niche_id, scripts=[],
            adequacy=adequacy,
            grounded_video_ids=[v.get("video_id", "") for v in videos],
            generated_for_date=target_date,
            error=f"duplicate_hook_types: {len(scripts_out)} distinct",
        )

    return RitualResult(
        user_id=user_id,
        niche_id=niche_id,
        scripts=scripts_out,
        adequacy=adequacy,
        grounded_video_ids=[v.get("video_id", "") for v in videos],
        generated_for_date=target_date,
        error=None,
    )


def upsert_ritual(client: Any, result: RitualResult) -> bool:
    """Write a successful RitualResult to daily_ritual. No-op on thin/errored.

    Returns True only when the DB write succeeds — callers must not count a
    user as generated until this confirms the row landed.
    """
    if result.error or not result.scripts:
        logger.info(
            "[ritual] skipping upsert user=%s reason=%s",
            result.user_id, result.error,
        )
        return False
    row = {
        "user_id":            result.user_id,
        "generated_for_date": result.generated_for_date.isoformat(),
        "niche_id":           result.niche_id,
        "scripts":            result.scripts,
        "adequacy":           result.adequacy,
        "grounded_video_ids": result.grounded_video_ids,
        "generated_at":       datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.table("daily_ritual").upsert(
            row,
            on_conflict="user_id,generated_for_date,niche_id",
        ).execute()
        return True
    except Exception as exc:
        logger.exception("[ritual] upsert failed user=%s: %s", result.user_id, exc)
        return False


# ── Batch orchestration ───────────────────────────────────────────────────

@dataclass
class RitualBatchSummary:
    generated: int = 0
    skipped_thin: int = 0
    failed_schema: int = 0
    failed_gemini: int = 0
    failed_duplicate_hooks: int = 0   # Gemini returned <3 distinct hook types
    failed_upsert: int = 0            # DB write failed after successful generation
    users_no_niche: int = 0


def run_morning_ritual_batch(
    client: Any,
    user_ids: list[str] | None = None,
) -> RitualBatchSummary:
    """Generate rituals for every profile with a niche set.

    Pass user_ids to restrict (dev smoke-test); omit for the nightly cron
    that hits everyone.
    """
    summary = RitualBatchSummary()

    # Up to 3 niches per profile in ``niche_ids``; legacy rows may only have
    # ``primary_niche`` until the user re-saves settings.
    query = client.table("profiles").select(
        "id, primary_niche, niche_ids, reference_channel_handles",
    )
    if user_ids:
        query = query.in_("id", user_ids)
    profiles = (query.execute().data or [])

    # Niche name lookup once.
    niche_rows = (
        client.table("niche_taxonomy").select("id, name_vn, name_en").execute().data or []
    )
    niche_name_map: dict[int, str] = {
        int(r["id"]): r.get("name_vn") or r.get("name_en") or str(r["id"])
        for r in niche_rows
    }

    for prof in profiles:
        raw = prof.get("niche_ids")
        nids: list[int] = []
        if isinstance(raw, list) and len(raw) > 0:
            for x in raw[:3]:
                try:
                    nids.append(int(x))
                except (TypeError, ValueError):
                    continue
        if not nids:
            pn = prof.get("primary_niche")
            if pn is not None:
                nids = [int(pn)]
        if not nids:
            summary.users_no_niche += 1
            continue
        for nid in nids:
            result = generate_ritual_for_user(
                client,
                user_id=prof["id"],
                niche_id=int(nid),
                niche_name=niche_name_map.get(int(nid), str(nid)),
                reference_handles=list(prof.get("reference_channel_handles") or []),
            )
            if result.error is None and result.scripts:
                if upsert_ritual(client, result):
                    summary.generated += 1
                else:
                    summary.failed_upsert += 1
            elif result.error and result.error.startswith("thin_corpus"):
                summary.skipped_thin += 1
            elif result.error and result.error.startswith("schema_error"):
                summary.failed_schema += 1
            elif result.error and result.error.startswith("gemini_error"):
                summary.failed_gemini += 1
            elif result.error and result.error.startswith("duplicate_hook_types"):
                summary.failed_duplicate_hooks += 1
    return summary


__all__ = [
    "CLAIM_TIERS",
    "HookTypeEn",
    "MIN_GROUNDING_VIDEOS",
    "RitualBatchSummary",
    "RitualBundle",
    "RitualResult",
    "RitualScript",
    "TARGET_GROUNDING_VIDEOS",
    "generate_ritual_for_user",
    "run_morning_ritual_batch",
    "upsert_ritual",
]
