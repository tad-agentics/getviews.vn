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
from getviews_pipeline.two_axis_taxonomy import extract_subject_matter_from_analysis_json
from getviews_pipeline.voice_lint import build_forbidden_phrases_prompt_block

logger = logging.getLogger(__name__)

_MORNING_RITUAL_FORBIDDEN_BLOCK = build_forbidden_phrases_prompt_block()

# PostgREST ``select=`` for batch ritual profile reads (PR6 — no ``primary_niche``).
# Exposed on ``/health`` so ops can ``curl`` the batch URL and confirm the
# deployed image matches this repo after a deploy.
PROFILE_SELECT_RITUAL_BATCH = "id,creator_niche_id,reference_channel_handles"


# ── Canonical hook-type enum (matches HOOK_TYPE_VI keys) ──────────────────
# Gemini must pick one of these 15 literals; we derive the Vietnamese
# display name post-hoc so the model can't drift from the fixed taxonomy.
HookTypeEn = Literal[
    "warning",
    "price_shock",
    "gia_soc",
    "shock_stat",
    "reaction",
    "comparison",
    "expose",
    "vach_tran",
    "controversy",
    "how_to",
    "tips_value",
    "story_open",
    "pov",
    "social_proof",
    "curiosity_gap",
    "bold_claim",
    "challenge",
    "question",
    "pain_point",
    "trend_hijack",
    "fomo_urgency",
    "dialect_identity",
    "insider",
    "secret",
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
                .select("video_id, creator_handle, views, analysis_json, thumbnail_url, hook_phrase, hook_type, scene_count, video_duration, engagement_rate")
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
                .select("video_id, creator_handle, views, analysis_json, thumbnail_url, hook_phrase, hook_type, scene_count, video_duration, engagement_rate")
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
                .select("video_id, creator_handle, views, analysis_json, thumbnail_url, hook_phrase, hook_type, scene_count, video_duration, engagement_rate")
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


_PROMPT_TEMPLATE = """Bạn là content strategist cho TikTok creator Việt Nam trong ngách **{niche_name}**.

Tạo 3 kịch bản video ĐỘC LẬP, mỗi cái dùng **một hook_type_en khác nhau** (không trùng).

## Grounding ({grounding_count} video nổi bật trong ngách 7 ngày qua)

Mỗi video có thể kèm `subject_matter` (một dòng tóm tắt chủ đề từ phân tích HI-9) — dùng để neo noun cụ thể trong title_vi khi có.

{grounding_json}

**Median của top winning videos**: {median_shot_count} shot, {median_length_sec} giây — dùng làm anchor cho shot_count + length_sec.
**Adequacy tier**: {adequacy_tier} — {adequacy_note}

## Cách suy nghĩ (làm theo thứ tự)

**Bước 1 — Trích pattern, không copy hook.** Đọc 20 hook ở grounding. Tìm 3 PATTERN khác nhau lặp lại ở các video high-view. Ví dụ pattern: "số liệu cụ thể + so sánh ngược trực giác", "POV người mới bắt đầu", "trước/sau 30 ngày". KHÔNG copy hook nguyên văn — chỉ rút khung.

**Bước 2 — Chọn cơ chế psychology cho mỗi script.** Mỗi `why_works` PHẢI nêu tên 1 cơ chế từ danh sách:
- `curiosity_gap`: tạo khoảng trống thông tin viewer cần lấp
- `social_proof`: ai đã làm + kết quả gì
- `identification`: viewer thấy "đó là mình" / "đúng tình huống tôi"
- `contrarian_take`: đi ngược common belief
- `before_after_promise`: hứa transformation cụ thể đo được
- `status_anchor`: gắn với identity / class viewer muốn thuộc về
- `fomo_loss`: nguy cơ bỏ lỡ / thiệt hại nếu không hành động
why_works phải giải thích MECHANISM = [tên cơ chế] HOẠT ĐỘNG NHƯ NÀO trong 1 câu, không generic ("tạo sự tò mò").

**Bước 3 — Chốt số liệu thực tế.** retention_est_pct, shot_count, length_sec phải bám median grounding. Nếu adequacy là "thin" / "none", retention_est_pct giữ trong 40-55% (không tự tin được). Nếu adequacy là "basic_citation" hoặc cao hơn, có thể lên 60-75% nếu pattern có lịch sử mạnh.

## Schema mỗi kịch bản

- `hook_type_en`: 1 literal trong enum cho phép.
- `title_vi`: câu hook creator đọc trực tiếp vào camera, trong "dấu ngoặc kép". ≤ 90 ký tự. Phải có **ít nhất 1 noun cụ thể từ ngách** (sản phẩm, địa danh, brand, action verb đặc trưng — KHÔNG generic).
- `why_works`: 1 câu Vietnamese, ≤ 140 ký tự. Format: "[mechanism_name] — [giải thích cụ thể trong 1 câu]". Ví dụ: "curiosity_gap — số 67% trong câu hook khiến viewer cần lý do, retention spike ở giây 3-5."
- `retention_est_pct`: integer 40-75. Bám adequacy tier như nói trên.
- `shot_count`: integer 2-8. Bám median grounding ± 1.
- `length_sec`: integer 15-90. Bám median grounding ± 5.

## Few-shot (ví dụ neo từ video nổi bật trong grounding)

{few_shot_json}

## Quy tắc cứng

- Title PHẢI tiếng Việt tự nhiên — không dịch Anh-Việt cứng (sai: "Đừng bỏ lỡ điều này"; đúng: "Tôi đã sai 3 năm").
- 3 kịch bản PHẢI đa dạng hook_type_en (không 3 pov, không 3 shock_stat).
- Tuân thủ khối Copy-rules sau cho `title_vi` và `why_works`.
- Thay cụm cấm bằng chi tiết từ grounding (số liệu, brand, creator, địa danh).

{forbidden_copy_block}
- KHÔNG lặp lại y nguyên hook video trong grounding — chỉ rút pattern.
{reference_note}"""


def _median(values: list[int]) -> int | None:
    """Plain median for small int lists. None on empty."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) // 2


_ADEQUACY_NOTES: dict[str, str] = {
    "none": "grounding rất mỏng, retention_est_pct giữ ≤55%; pattern còn unreliable, viết hook conservative.",
    "thin": "grounding mỏng, retention_est_pct giữ 45-60%; tránh promise mạnh.",
    "reference_pool": "grounding ok từ kênh tham chiếu, retention 50-70% là realistic.",
    "basic_citation": "grounding tốt, retention 55-72% nếu pattern lặp ≥3 video.",
    "niche_norms": "grounding mạnh + đủ sample, retention 60-75% cho pattern hot.",
}


def _dynamic_few_shot_json(videos: list[dict[str, Any]], niche_name: str) -> str:
    """ME-14 — one JSON example from the top-view grounding row (not hard-coded Beauty)."""
    if not videos:
        return json.dumps(
            {
                "hook_type_en": "before_after",
                "title_vi": '"30 ngày dùng tretinoin 0.025% — đây là khuôn mặt tôi mỗi tuần"',
                "why_works": "before_after_promise — promise transformation đo được theo tuần buộc viewer xem hết để thấy kết quả tuần 4.",
                "retention_est_pct": 62,
                "shot_count": 5,
                "length_sec": 30,
            },
            ensure_ascii=False,
            indent=2,
        )

    top = max(videos, key=lambda v: int(v.get("views") or 0))
    hook_type_en = str(top.get("hook_type") or "before_after")
    raw_phrase = str(top.get("hook_phrase") or "").strip()
    if not raw_phrase:
        sm = extract_subject_matter_from_analysis_json(top.get("analysis_json"))
        raw_phrase = (sm or "").strip()
    if not raw_phrase:
        raw_phrase = f"Neo cụ thể từ ngách {niche_name} — không copy nguyên hook."
    if len(raw_phrase) > 88:
        raw_phrase = raw_phrase[:85] + "…"

    try:
        er = float(top.get("engagement_rate") or 0)
    except (TypeError, ValueError):
        er = 0.0
    retention_est_pct = int(max(40, min(75, round(52 + min(23, er * 400)))))

    shots = top.get("scene_count")
    try:
        shot_count = int(shots) if shots is not None else 4
    except (TypeError, ValueError):
        shot_count = 4
    shot_count = max(2, min(8, shot_count))

    vd = top.get("video_duration")
    try:
        length_sec = int(vd) if vd is not None else 30
    except (TypeError, ValueError):
        length_sec = 30
    length_sec = max(15, min(90, length_sec))

    views = int(top.get("views") or 0)
    vid = str(top.get("video_id") or "")
    why = (
        f"curiosity_gap — neo theo hook đã chứng minh {views:,} views trong grounding "
        f"(video_id={vid}); giữ mechanism khớp hook_type_en={hook_type_en}."
    )
    if len(why) > 200:
        why = why[:197] + "…"

    example = {
        "hook_type_en": hook_type_en,
        "title_vi": f'"{raw_phrase}"',
        "why_works": why,
        "retention_est_pct": retention_est_pct,
        "shot_count": shot_count,
        "length_sec": length_sec,
    }
    return json.dumps(example, ensure_ascii=False, indent=2)


def _build_prompt(
    niche_name: str,
    videos: list[dict[str, Any]],
    reference_handles: list[str],
    adequacy: str = "thin",
) -> str:
    # Trim the grounding payload so the prompt doesn't balloon — Gemini
    # only needs hook + hook_type + views + counts per row to pattern-match.
    trimmed = []
    for v in videos:
        row = {
            "video_id": v.get("video_id"),
            "creator": v.get("creator_handle"),
            "views":   v.get("views"),
            "hook_type": v.get("hook_type"),
            "hook_phrase": v.get("hook_phrase"),
            "scene_count": v.get("scene_count"),
            "length_sec": v.get("video_duration"),
            "engagement_rate": v.get("engagement_rate"),
        }
        sm = extract_subject_matter_from_analysis_json(v.get("analysis_json"))
        if sm:
            row["subject_matter"] = sm
        trimmed.append(row)

    # Median anchors for shot_count + length_sec — tells Gemini what
    # "realistic" looks like in this specific niche's winning videos
    # rather than relying on a hard-coded 3-6 / 20-45 range.
    shot_counts = [int(v.get("scene_count")) for v in videos if v.get("scene_count") is not None]
    durations = [int(v.get("video_duration")) for v in videos if v.get("video_duration") is not None]
    median_shot_count = _median(shot_counts) or 4
    median_length_sec = _median(durations) or 30

    reference_note = ""
    if reference_handles:
        handles_fmt = ", ".join(f"@{h}" for h in reference_handles[:3])
        reference_note = (
            f"\n- Ưu tiên giọng + phong cách giống các kênh tham chiếu của creator: {handles_fmt}."
        )

    adequacy_note = _ADEQUACY_NOTES.get(adequacy, _ADEQUACY_NOTES["thin"])

    return _PROMPT_TEMPLATE.format(
        niche_name=niche_name,
        grounding_count=len(videos),
        grounding_json=json.dumps(trimmed, ensure_ascii=False, indent=2),
        few_shot_json=_dynamic_few_shot_json(videos, niche_name),
        median_shot_count=median_shot_count,
        median_length_sec=median_length_sec,
        adequacy_tier=adequacy,
        adequacy_note=adequacy_note,
        reference_note=reference_note,
        forbidden_copy_block=_MORNING_RITUAL_FORBIDDEN_BLOCK,
    )


# ── Sound Radar enrichment (L2.2 Sprint 3) ─────────────────────────────────


def _urgency_band_for(velocity: str | None) -> str | None:
    """Map a Sound Radar bucket label to a creator-facing urgency band.

    The FE renders this as the small "Đăng trong 48h" / "Tuần này" /
    "Bất kỳ" badge next to the sound name. None → omit the urgency
    badge entirely (script falls back to the L1.4 sound-less render).
    """
    if velocity == "accelerating":
        return "post_within_48h"
    if velocity == "peaking":
        return "this_week"
    return None


def _fetch_sound_recommendations(
    client: Any,
    niche_id: int,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Pull this week's accelerating sounds for the niche, in priority order.

    Reads ``trend_velocity.sound_trends`` (Sound Radar — populated by
    ``cron-batch-trend-velocity``). Prefers ``accelerating`` (highest-
    leverage post-NOW signal), then ``peaking`` (moderate). Skips
    ``cooling`` and unbucketed sounds — we only recommend things worth
    posting against this week.

    Returns up to ``limit`` dicts, each shaped to drop directly onto a
    ritual script via ``script_obj.update(...)``:

      ``{
         "sound_id":      "...",
         "sound_name":    "...",
         "sound_velocity": "accelerating" | "peaking",
         "sound_delta_pct": 200.0 | None,
         "urgency_band":  "post_within_48h" | "this_week",
      }``

    Empty list on any failure or when no recommendations exist —
    callers treat that as "ritual scripts ship without sound this
    cycle, identical to pre-Sprint-3 UX".
    """
    if client is None or niche_id is None:
        return []
    try:
        res = (
            client.table("trend_velocity")
            .select("sound_trends, week_start")
            .eq("niche_id", niche_id)
            .order("week_start", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.warning(
            "[ritual/sound] niche=%s trend_velocity fetch failed: %s",
            niche_id, exc,
        )
        return []

    if not rows:
        return []
    sound_trends = rows[0].get("sound_trends") or {}

    out: list[dict[str, Any]] = []
    # Priority order matters — top accelerating sound goes to script 1
    # (the highest-billed idea on the StudioHero row), peaking fills
    # remaining slots only if accelerating ran out.
    for label in ("accelerating", "peaking"):
        for entry in sound_trends.get(label) or []:
            sid = entry.get("sound_id")
            name = entry.get("name") or sid
            if not sid or not name:
                continue
            band = _urgency_band_for(label)
            delta = entry.get("delta_pct")
            # delta_pct=9999 is the "brand-new this week" sentinel from
            # _compute_sound_trends_for_niche; surface it as None on
            # the FE so we don't render a misleading "+9999%" string.
            if isinstance(delta, (int, float)) and delta >= 9000:
                delta = None
            out.append({
                "sound_id":        sid,
                "sound_name":      name,
                "sound_velocity":  label,
                "sound_delta_pct": delta,
                "urgency_band":    band,
            })
            if len(out) >= limit:
                return out
    return out


# ── Evidence strip (L2.2 Sprint 4) ─────────────────────────────────────────


EVIDENCE_PER_SCRIPT = 12
EVIDENCE_MIN_HOOK_MATCH = 4   # below this, top up with top-of-pool fallback


def _pick_evidence_for_script(
    pool: list[dict[str, Any]],
    hook_type_en: str,
    *,
    limit: int = EVIDENCE_PER_SCRIPT,
) -> list[str]:
    """Pick up to ``limit`` corpus video_ids that prove the hook works.

    Strategy:
      1. Filter ``pool`` by ``hook_type == hook_type_en`` (case-insensitive,
         pool order = views-DESC) — these are the strongest evidence.
      2. If the filtered set is < ``EVIDENCE_MIN_HOOK_MATCH``, top up with
         the highest-views videos from ``pool`` that aren't already in the
         filtered set. Better to show a mixed-hook strip than nothing.

    The pool itself is already DESC-sorted by views (see
    ``_fetch_grounding_videos``), so taking-from-the-top preserves the
    "what's actually winning" ordering the FE renders.

    Returns a deduped list of video_id strings (empty when ``pool`` is
    empty or no entries have a video_id).
    """
    if not pool:
        return []
    target = (hook_type_en or "").strip().lower()

    matched: list[str] = []
    fallback: list[str] = []
    for v in pool:
        vid = v.get("video_id")
        if not isinstance(vid, str) or not vid:
            continue
        v_hook = str(v.get("hook_type") or "").strip().lower()
        if target and v_hook == target:
            matched.append(vid)
        else:
            fallback.append(vid)

    if len(matched) >= EVIDENCE_MIN_HOOK_MATCH:
        return matched[:limit]
    # Mix: matched first (preserves "this hook won here" framing), then
    # fallback by views to fill up to limit.
    out = list(matched)
    for vid in fallback:
        if len(out) >= limit:
            break
        out.append(vid)
    return out[:limit]


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

    prompt = _build_prompt(niche_name, videos, reference_handles, adequacy=adequacy)
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
            call_site="morning_ritual",
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

    # L2.2 Sprint 3 — Sound Radar enrichment. Distribute one
    # accelerating/peaking sound per ritual script so the StudioHero
    # row renders "🔊 [Sound] · 🔥 Đăng trong 48h" alongside the hook.
    # Pre-Sprint-3 rituals have zero sound fields; the FE falls back
    # to the un-enriched render path — graceful both directions.
    sound_recs = _fetch_sound_recommendations(client, niche_id, limit=len(scripts_out))
    for i, rec in enumerate(sound_recs):
        if i >= len(scripts_out):
            break
        scripts_out[i].update(rec)

    # L2.2 Sprint 4 — per-script evidence strip. Each ritual row gets up
    # to 12 video_ids from the grounding pool that match the script's
    # hook_type, so the FE can hydrate thumbnails on-demand and prove
    # "this hook is winning right now in your niche". Falls back to top-
    # of-pool when fewer than 4 hook-matched videos exist. Pre-Sprint-4
    # ritual rows have no ``evidence_video_ids`` field and the FE
    # gracefully omits the strip.
    for item in scripts_out:
        item["evidence_video_ids"] = _pick_evidence_for_script(
            videos, item.get("hook_type_en", ""),
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
    # Audit Pass-3 fix #3 — count per-user uncaught exceptions so the
    # batch loop can continue when ``generate_ritual_for_user`` raises
    # something its internal try/except blocks don't catch (e.g. an SDK
    # bubble-up from outside the fetch + Gemini guards). Without the
    # outer catch-all, the entire batch aborted at the first uncaught
    # error and remaining users got nothing.
    failed_unhandled: int = 0


def run_morning_ritual_batch(
    client: Any,
    user_ids: list[str] | None = None,
) -> RitualBatchSummary:
    """Generate rituals for every profile with a niche set.

    Pass user_ids to restrict (dev smoke-test); omit for the nightly cron
    that hits everyone.
    """
    summary = RitualBatchSummary()

    # Single niche per user. Two-axis refactor PR5 — read the canonical
    # ``creator_niche_id`` (from PR3, backfilled for all rows) and resolve
    # to the representative legacy ``niche_taxonomy.id`` so downstream
    # ritual generation (which queries video_corpus.niche_id) works unchanged.
    from getviews_pipeline.profile_niches import resolve_legacy_niche_from_profile_row

    query = client.table("profiles").select(PROFILE_SELECT_RITUAL_BATCH)
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
        nid = resolve_legacy_niche_from_profile_row(prof)
        if nid is None:
            summary.users_no_niche += 1
            continue
        # Audit Pass-3 fix #3 — outer catch-all so an uncaught
        # exception from ``generate_ritual_for_user`` (anything its
        # internal per-step try/except doesn't intercept — e.g. a
        # Pydantic schema mismatch on a fresh Gemini SDK version,
        # a Supabase connection drop) doesn't kill the rest of the
        # batch. Each user is independent; one bad run shouldn't
        # rob 99 other creators of their daily ritual.
        try:
            result = generate_ritual_for_user(
                client,
                user_id=prof["id"],
                niche_id=nid,
                niche_name=niche_name_map.get(nid, str(nid)),
                reference_handles=list(prof.get("reference_channel_handles") or []),
            )
        except Exception as exc:
            logger.exception(
                "[ritual] uncaught exception user=%s niche=%s: %s",
                prof.get("id"), nid, exc,
            )
            summary.failed_unhandled += 1
            continue
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
    "EVIDENCE_PER_SCRIPT",
    "HookTypeEn",
    "MIN_GROUNDING_VIDEOS",
    "PROFILE_SELECT_RITUAL_BATCH",
    "RitualBatchSummary",
    "RitualBundle",
    "RitualResult",
    "RitualScript",
    "TARGET_GROUNDING_VIDEOS",
    "generate_ritual_for_user",
    "run_morning_ritual_batch",
    "upsert_ritual",
]
