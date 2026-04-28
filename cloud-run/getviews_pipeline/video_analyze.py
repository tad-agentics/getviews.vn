"""Phase B · B.1.3 — /video/analyze: cache, structural slots, Gemini LLM, diagnostics upsert.

Deterministic pieces reuse ``video_structural`` + ``video_niche_benchmark``.
Writes go through **service_role** (see migration: no authenticated INSERT).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from getviews_pipeline.video_niche_benchmark import (
    build_niche_benchmark_payload,
    fetch_niche_intelligence_sync,
)
from getviews_pipeline.video_structural import (
    decompose_segments,
    extract_hook_phases,
    model_retention_curve,
    video_duration_sec,
)

logger = logging.getLogger(__name__)

DIAGNOSTICS_STALE_AFTER = timedelta(hours=1)


def _fetch_sidecars_sync(
    video_id: str,
    comment_count_hint: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Run async thumbnail + comment-radar resolvers from the sync pipeline (thread pool)."""
    from getviews_pipeline.comment_radar_cache import resolve_comment_radar
    from getviews_pipeline.thumbnail_analysis_cache import resolve_thumbnail_analysis

    async def _both() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return await asyncio.gather(
            resolve_thumbnail_analysis(video_id),
            resolve_comment_radar(video_id, comment_count_hint=comment_count_hint),
        )

    return asyncio.run(_both())


def _merge_sidecars_into_response(
    out: dict[str, Any],
    *,
    video_id: str,
    comment_count_hint: int,
) -> dict[str, Any]:
    """Attach corpus sidecars; failures are logged and omitted from the payload."""
    try:
        thumb, radar = _fetch_sidecars_sync(video_id, comment_count_hint)
    except Exception as exc:
        logger.warning(
            "[video_analyze] sidecar resolve failed video_id=%s: %s",
            video_id,
            exc,
        )
        return out
    if thumb is not None:
        out["thumbnail_analysis"] = thumb
    if radar is not None:
        out["comment_radar"] = radar
    return out


# ── Gemini output schemas (text-only, JSON) ───────────────────────────────


class LessonSlot(BaseModel):
    title: str = Field(max_length=120)
    body: str = Field(max_length=800)


class WinAnalysisLLM(BaseModel):
    analysis_headline: str = Field(max_length=200)
    analysis_subtext: str = Field(max_length=700)
    lessons: list[LessonSlot] = Field(min_length=3, max_length=3)
    hook_bodies: list[str] = Field(
        min_length=3,
        max_length=3,
        description="Vietnamese body copy for the 3 hook-phase cards, in time order.",
    )


class FlopIssueLLM(BaseModel):
    sev: Literal["high", "mid", "low"]
    t: float = Field(ge=0.0, le=600.0)
    end: float = Field(ge=0.0, le=600.0)
    title: str = Field(max_length=200)
    detail: str = Field(max_length=900)
    fix: str = Field(max_length=400)


class FlopHeadline(BaseModel):
    """Structured flop H1 segments; stored JSON-serialised in ``video_diagnostics.analysis_headline``."""

    prefix: str = Field(max_length=120, description='e.g. "Video dừng ở"')
    view_accent: str = Field(max_length=40, description='e.g. "8.4K view"')
    middle: str = Field(max_length=200, description="Diagnosis clause between view and prediction.")
    prediction_pos: str = Field(max_length=40, description='e.g. "~34K"')
    suffix: str = Field(max_length=120, description="Closing punctuation or short tail.")

    @model_validator(mode="after")
    def _total_chars_le_400(self) -> FlopHeadline:
        total = len(self.prefix) + len(self.view_accent) + len(self.middle) + len(self.prediction_pos) + len(
            self.suffix
        )
        if total > 400:
            raise ValueError(f"FlopHeadline total length {total} exceeds 400")
        return self


class FlopAnalysisLLM(BaseModel):
    analysis_headline: FlopHeadline
    flop_issues: list[FlopIssueLLM] = Field(min_length=1, max_length=8)


# ── Mode + KPI helpers ─────────────────────────────────────────────────────


def _median_views_proxy(niche_row: dict[str, Any] | None) -> float:
    if not niche_row:
        return 10_000.0
    o = float(niche_row.get("organic_avg_views") or 0)
    c = float(niche_row.get("commerce_avg_views") or 0)
    if o > 0 and c > 0:
        return (o + c) / 2.0
    return max(o, c, 5_000.0)


def is_flop_mode(video: dict[str, Any], niche_row: dict[str, Any] | None) -> bool:
    """Heuristic from phase-b-plan: views or engagement vs niche medians."""
    views = int(video.get("views") or 0)
    er = float(video.get("engagement_rate") or 0.0)
    if not niche_row:
        return False
    niche_views = _median_views_proxy(niche_row)
    median_er = float(niche_row.get("median_er") or 0.04)
    if niche_views > 0 and views < niche_views * 0.5:
        return True
    if median_er > 0 and er < median_er * 0.6:
        return True
    return False


def projected_views_heuristic(
    views: int,
    niche_avg_views: int,
    flop_issues: list[dict[str, Any]],
) -> int:
    high = sum(1 for x in flop_issues if str(x.get("sev")) == "high")
    base = max(int(niche_avg_views * 0.35), int(views * 2.2))
    boost = int(high * niche_avg_views * 0.06)
    # No niche row / avg_views=0: skip niche-relative cap (otherwise cap=0 → min(0, …)=0).
    if niche_avg_views <= 0:
        return max(0, base + boost)
    cap = max(niche_avg_views, int(niche_avg_views * 1.15))
    return min(cap, base + boost)


def _fmt_int_short(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return str(n)


def build_kpis(
    video: dict[str, Any],
    niche_meta: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    retention_end_pct: float,
) -> list[dict[str, str]]:
    views = int(video.get("views") or 0)
    shares = int(video.get("shares") or 0)
    saves = int(video.get("saves") or 0)
    niche_avg = max(int(niche_meta.get("avg_views") or 0), 1)
    mult = views / niche_avg if niche_avg else 0.0
    delta_views = f"{mult:.1f}× kênh" if mult >= 0.1 else "—"
    ret_pct = f"{retention_end_pct:.0f}%"
    ret_delta = "top 5%" if retention_end_pct >= 70 else "ngách TB"
    save_rate = (saves / views * 100.0) if views else 0.0
    sr_delta = "rất cao" if save_rate > 2.0 else "TB"
    return [
        {"label": "VIEW", "value": _fmt_int_short(views), "delta": delta_views},
        {"label": "GIỮ CHÂN", "value": ret_pct, "delta": ret_delta},
        {"label": "SAVE RATE", "value": f"{save_rate:.1f}%", "delta": sr_delta},
        {"label": "SHARE", "value": _fmt_int_short(shares), "delta": "lan toả"},
    ]


def _parse_ts(ts: Any) -> datetime | None:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    try:
        s = str(ts).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _diagnostics_fresh(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return False
    return datetime.now(UTC) - ct < DIAGNOSTICS_STALE_AFTER


def _cache_age_minutes(row: dict[str, Any]) -> int:
    ct = _parse_ts(row.get("computed_at"))
    if not ct:
        return 0
    delta = datetime.now(UTC) - ct
    return max(0, int(delta.total_seconds() // 60))


def _fetch_corpus_row(user_sb: Any, vid: str) -> dict[str, Any]:
    """Load one ``video_corpus`` row; never surfaces PostgREST 0-row as a 500."""
    from postgrest.exceptions import APIError

    cols = (
        "video_id,creator_handle,views,likes,comments,shares,saves,save_rate,"
        "engagement_rate,thumbnail_url,created_at,niche_id,analysis_json,"
        "breakout_multiplier,tiktok_url"
    )
    try:
        vres = user_sb.table("video_corpus").select(cols).eq("video_id", vid).maybe_single().execute()
    except APIError as exc:
        code = getattr(exc, "code", None)
        details = str(getattr(exc, "details", "") or "")
        if code == "PGRST116" or "0 rows" in details:
            raise ValueError("video not in corpus") from exc
        raise
    if vres is None:
        raise ValueError("video not in corpus")
    data = getattr(vres, "data", None)
    if not isinstance(data, dict) or not data.get("video_id"):
        raise ValueError("video not in corpus")
    return data


def _coerce_analysis_headline_for_api(raw: Any, mode: Literal["win", "flop"]) -> Any:
    """Win: plain string. Flop: parse JSON ``FlopHeadline`` from TEXT column; legacy plain string passthrough."""
    if mode == "win":
        if raw is None:
            return None
        return raw if isinstance(raw, str) else str(raw)

    if raw is None:
        return None
    if isinstance(raw, dict):
        try:
            return FlopHeadline.model_validate(raw).model_dump()
        except Exception:
            logger.warning("[video_analyze] flop headline dict failed FlopHeadline validation")
            return str(raw)

    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("{"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return FlopHeadline.model_validate(parsed).model_dump()
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("[video_analyze] flop headline JSON invalid: %s", exc)
        return s

    return str(raw)


def _resolve_niche_label(user_sb: Any, niche_id: int) -> str:
    """``niche_taxonomy.name_vn`` preferred; empty string if missing or lookup fails."""
    if not niche_id:
        return ""
    try:
        tres = (
            user_sb.table("niche_taxonomy")
            .select("name_vn,name_en")
            .eq("id", niche_id)
            .limit(1)
            .execute()
        )
        tr = (tres.data or [{}])[0]
        return str(tr.get("name_vn") or tr.get("name_en") or "")
    except Exception:
        return ""


def _response_from_diagnostics_row(
    video: dict[str, Any],
    diag: dict[str, Any],
    *,
    mode: Literal["win", "flop"],
    niche_meta: dict[str, Any],
    niche_benchmark: list[dict[str, float]],
    retention_user: list[dict[str, float]],
    niche_label: str,
    retention_source: Literal["real", "modeled"] = "modeled",
) -> dict[str, Any]:
    analysis = video.get("analysis_json") or {}
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError:
            analysis = {}
    if not isinstance(analysis, dict):
        analysis = {}
    dur = video_duration_sec(analysis)
    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    title_hint = str(hook.get("hook_phrase") or "")[:200]
    ret_curve = diag.get("retention_curve") or retention_user
    bench_curve = diag.get("niche_benchmark_curve") or niche_benchmark
    ret_end = float(ret_curve[-1]["pct"]) if ret_curve else 0.0
    return {
        "video_id": video["video_id"],
        "mode": mode,
        "meta": {
            "creator": video.get("creator_handle") or "",
            "views": int(video.get("views") or 0),
            "likes": int(video.get("likes") or 0),
            "comments": int(video.get("comments") or 0),
            "shares": int(video.get("shares") or 0),
            "save_rate": float(video.get("save_rate") or 0.0)
            if video.get("save_rate") is not None
            else (int(video.get("saves") or 0) / max(int(video.get("views") or 1), 1)),
            "duration_sec": dur,
            "thumbnail_url": video.get("thumbnail_url"),
            "date_posted": (video.get("created_at") or "")[:10]
            if video.get("created_at")
            else None,
            "title": title_hint or None,
            "niche_label": niche_label or None,
            "retention_source": retention_source,
        },
        "kpis": build_kpis(video, niche_meta, mode=mode, retention_end_pct=ret_end),
        "segments": diag.get("segments") or [],
        "hook_phases": diag.get("hook_phases") or [],
        "lessons": diag.get("lessons") or [],
        "analysis_headline": _coerce_analysis_headline_for_api(diag.get("analysis_headline"), mode),
        "analysis_subtext": diag.get("analysis_subtext"),
        "flop_issues": diag.get("flop_issues"),
        "retention_curve": ret_curve,
        "niche_benchmark_curve": bench_curve,
        "niche_meta": niche_meta,
    }


def _call_win_gemini(
    *,
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_label: str,
) -> WinAnalysisLLM:
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    prompt = f"""Bạn là biên tập TikTok tiếng Việt. Viết JSON theo schema cho màn "Vì sao video NỔ".

Ngách: {niche_label}
Video: creator @{video.get("creator_handle","")} | views ~{int(video.get("views") or 0)}
Hook phrase: {hook.get("hook_phrase") or ""}
Hook type: {hook.get("hook_type") or ""}

Quy tắc:
- Headline + subtext súc tích, không sáo rỗng, không cụm cấm trong playbook GetViews.
- 3 lessons: title ngắn + body 1-2 câu, khả năng áp dụng thực tế.
- hook_bodies: đúng 3 đoạn cho 3 ô 0.0–0.8s / 0.8–1.8s / 1.8–3.0s — mỗi đoạn 2-4 câu tiếng Việt, mô tả cơ chế hook (không copy nguyên hook phrase).
"""
    config = types.GenerateContentConfig(
        temperature=0.55,
        response_mime_type="application/json",
        response_json_schema=WinAnalysisLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return WinAnalysisLLM.model_validate_json(_normalize_response(raw))


def _call_flop_gemini(
    *,
    video: dict[str, Any],
    analysis: dict[str, Any],
    niche_label: str,
    niche_row: dict[str, Any] | None,
) -> FlopAnalysisLLM:
    from google.genai import types

    from getviews_pipeline.config import GEMINI_SYNTHESIS_FALLBACKS, GEMINI_SYNTHESIS_MODEL
    from getviews_pipeline.gemini import (
        _generate_content_models,
        _normalize_response,
        _response_text,
    )

    hook = (analysis.get("hook_analysis") or {}) if isinstance(analysis.get("hook_analysis"), dict) else {}
    niche_hint = json.dumps(niche_row or {}, ensure_ascii=False)[:2500]
    prompt = f"""Bạn là chẩn đoán cấu trúc TikTok tiếng Việt. Video đang FLOP so với ngách.

Ngách: {niche_label}
Context niche (JSON rút gọn): {niche_hint}
Video: @{video.get("creator_handle","")} | views {int(video.get("views") or 0)} | ER {float(video.get("engagement_rate") or 0):.4f}
Hook phrase: {hook.get("hook_phrase") or ""}

Trả về JSON theo schema:
- analysis_headline: object với đúng 5 trường (tiếng Việt, không HTML):
  - prefix: mở đầu ngắn (vd "Video dừng ở")
  - view_accent: cụm view ngắn (vd "8.4K view") — số khớp views video
  - middle: chẩn đoán flop (hook/scene…)
  - prediction_pos: dự đoán ngắn có dấu ~ (vd "~34K") NẾU có con số cụ thể;
    NẾU KHÔNG có dự báo thì TRẢ VỀ CHUỖI RỖNG "" — KHÔNG dùng "~0", "~—"
    hay placeholder giả. Người dùng sẽ đọc câu nối liền 5 đoạn.
  - suffix: kết (vd "." hoặc " nếu áp fix.")
  Tổng độ dài nối 5 chuỗi ≤ 400 ký tự.
- flop_issues: 3-6 mục, sắp xếp theo ảnh hưởng. sev high/mid/low. t/end là giây trên timeline. detail + fix cụ thể, tiếng Việt.
"""
    config = types.GenerateContentConfig(
        temperature=0.45,
        response_mime_type="application/json",
        response_json_schema=FlopAnalysisLLM.model_json_schema(),
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_SYNTHESIS_MODEL,
        fallbacks=GEMINI_SYNTHESIS_FALLBACKS,
        config=config,
    )
    raw = _response_text(response)
    return FlopAnalysisLLM.model_validate_json(_normalize_response(raw))


_CORPUS_ROW_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def resolve_video_id(sb: Any, *, video_id: str | None, tiktok_url: str | None) -> str:
    """Resolve whatever the caller passed into the canonical TikTok aweme_id.

    Accepts three shapes for `video_id`:
      - TikTok aweme_id (a numeric string like "7630766288574369045") —
        the canonical shape, returned as-is.
      - video_corpus.id (UUID) — some frontend callers (notably the
        Explore grid at src/routes/_app/trends/ExploreScreen.tsx) pass
        the corpus row PK instead of the aweme_id because the
        ExploreGridVideo type only exposes the row id. Tolerate it by
        looking the row up and returning its aweme_id.
      - empty → fall through to tiktok_url lookup.

    The UUID path exists because the shared URL vocab `?video_id=` is
    semantically ambiguous; fixing every call site would touch more
    code than fixing the resolver once. A surface-level frontend fix
    would also make sense for future cleanliness but doesn't change
    the server-side guarantee.
    """
    if video_id and str(video_id).strip():
        vid = str(video_id).strip()
        # UUID shape → treat as corpus row id, not aweme_id.
        if _CORPUS_ROW_UUID_RE.match(vid):
            res = (
                sb.table("video_corpus")
                .select("video_id")
                .eq("id", vid)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                raise ValueError("Không tìm thấy video trong corpus cho id này")
            return str(rows[0]["video_id"])
        return vid
    if not tiktok_url or not str(tiktok_url).strip():
        raise ValueError("Cần video_id hoặc tiktok_url")
    url = str(tiktok_url).strip()
    res = (
        sb.table("video_corpus")
        .select("video_id")
        .eq("tiktok_url", url)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise ValueError("Không tìm thấy video trong corpus cho URL này")
    return str(rows[0]["video_id"])


def run_video_analyze_pipeline(
    service_sb: Any,
    user_sb: Any,
    *,
    video_id: str | None,
    tiktok_url: str | None,
    force_refresh: bool = False,
    mode: Literal["win", "flop"] | None = None,
) -> dict[str, Any]:
    """Sync pipeline: read cache, else compute + Gemini + upsert. Returns API dict.

    When ``force_refresh`` is True, skip the 1h ``video_diagnostics`` TTL and
    always re-run Gemini + curve modeling (then upsert). Intended for debugging
    / prompt iteration only.

    When ``mode`` is ``"win"`` or ``"flop"``, that branch is used instead of
    the ``is_flop_mode`` heuristic. Because ``video_diagnostics`` is keyed only
    by ``video_id`` (one row holds either win- or flop-shaped analysis from the
    last run), a mode override always skips the fresh-diagnostics cache — same
    as an implicit ``force_refresh`` — so the response matches the requested path
    and the row is recomputed/upserted.
    """
    vid = resolve_video_id(user_sb, video_id=video_id, tiktok_url=tiktok_url)

    dres = (
        user_sb.table("video_diagnostics")
        .select("*")
        .eq("video_id", vid)
        .limit(1)
        .execute()
    )
    diag_row = (dres.data or [None])[0]

    video = _fetch_corpus_row(user_sb, vid)

    niche_id = int(video.get("niche_id") or 0)
    niche_intel = fetch_niche_intelligence_sync(user_sb, niche_id) if niche_id else None
    default_niche_meta = {
        "avg_views": 0,
        "avg_retention": 0.5,
        "avg_ctr": 0.04,
        "sample_size": 0,
        "winners_sample_size": None,
    }
    if isinstance(video.get("analysis_json"), str):
        try:
            analysis = json.loads(video["analysis_json"])
        except json.JSONDecodeError:
            analysis = {}
    else:
        analysis = video.get("analysis_json") or {}
    if not isinstance(analysis, dict):
        analysis = {}
    dur = video_duration_sec(analysis)

    mode_override = mode is not None
    bypass_cache = force_refresh or mode_override
    if mode in ("win", "flop"):
        mode_resolved: Literal["win", "flop"] = mode
    else:
        mode_resolved = "flop" if is_flop_mode(video, niche_intel) else "win"

    if mode_override:
        logger.info(
            "[video_analyze] mode override: bypassing diagnostics cache video_id=%s mode=%s",
            vid,
            mode,
        )

    bench_payload = build_niche_benchmark_payload(
        niche_intel,
        niche_id=niche_id or 0,
        duration_sec=max(dur, 5.0),
        user_sb=user_sb,
    )
    niche_benchmark = bench_payload["niche_benchmark_curve"]
    niche_meta = bench_payload["niche_meta"] if bench_payload.get("niche_meta") is not None else default_niche_meta
    rs = bench_payload.get("retention_source") or "modeled"
    retention_source: Literal["real", "modeled"] = "real" if rs == "real" else "modeled"

    niche_label_resolved = _resolve_niche_label(user_sb, niche_id) if niche_id else ""

    bm = float(video.get("breakout_multiplier") or 1.0)
    retention_user = model_retention_curve(
        max(dur, 5.0),
        niche_median_retention=float(niche_meta["avg_retention"]),
        breakout_multiplier=bm,
        n_points=20,
    )

    if diag_row and _diagnostics_fresh(diag_row) and not bypass_cache:
        age_min = _cache_age_minutes(diag_row)
        logger.info(
            "[video_analyze] cache hit: video_id=%s age_min=%d force_refresh=%s",
            vid,
            age_min,
            force_refresh,
        )
        base = _response_from_diagnostics_row(
            video,
            diag_row,
            mode=mode_resolved,
            niche_meta=niche_meta,
            niche_benchmark=niche_benchmark,
            retention_user=retention_user,
            niche_label=niche_label_resolved,
            retention_source=retention_source,
        )
        return _merge_sidecars_into_response(
            base,
            video_id=vid,
            comment_count_hint=int(video.get("comments") or 0),
        )

    # Gemini prompt label: last-resort literal when taxonomy row is missing.
    gemini_niche_label = niche_label_resolved or (f"niche_{niche_id}" if niche_id else "unknown")
    if not niche_label_resolved and niche_id:
        logger.warning(
            "[video_analyze] niche label fallback niche_%s for Gemini video_id=%s",
            niche_id,
            vid,
        )

    segments = decompose_segments(analysis)
    hook_cards = extract_hook_phases(analysis)

    if mode_resolved == "win":
        llm = _call_win_gemini(video=video, analysis=analysis, niche_label=gemini_niche_label)
        for i, body in enumerate(llm.hook_bodies[:3]):
            if i < len(hook_cards):
                hook_cards[i]["body"] = body
        lessons = [x.model_dump() for x in llm.lessons]
        headline = llm.analysis_headline
        subtext = llm.analysis_subtext
        flop_issues = None
        projected = None
    else:
        llm = _call_flop_gemini(
            video=video, analysis=analysis, niche_label=gemini_niche_label, niche_row=niche_intel
        )
        headline = llm.analysis_headline.model_dump_json()
        subtext = None
        lessons = []
        flop_issues = [x.model_dump() for x in llm.flop_issues]
        projected = projected_views_heuristic(
            int(video.get("views") or 0),
            int(niche_meta["avg_views"] or 0),
            flop_issues,
        )

    upsert_payload = {
        "video_id": vid,
        "analysis_headline": headline,
        "analysis_subtext": subtext,
        "lessons": lessons,
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": flop_issues,
        "retention_curve": retention_user,
        "niche_benchmark_curve": niche_benchmark,
        "computed_at": datetime.now(UTC).isoformat(),
    }
    try:
        service_sb.table("video_diagnostics").upsert(
            upsert_payload,
            on_conflict="video_id",
        ).execute()
    except Exception as exc:
        logger.exception("[video_analyze] upsert failed video_id=%s: %s", vid, exc)
        raise

    diag_read = upsert_payload
    out = _response_from_diagnostics_row(
        video,
        diag_read,
        mode=mode_resolved,
        niche_meta=niche_meta,
        niche_benchmark=niche_benchmark,
        retention_user=retention_user,
        niche_label=niche_label_resolved,
        retention_source=retention_source,
    )
    if projected is not None:
        out["projected_views"] = projected
    return _merge_sidecars_into_response(
        out,
        video_id=vid,
        comment_count_hint=int(video.get("comments") or 0),
    )


# ── On-demand analysis (URL not in corpus) ────────────────────────────────


def _build_video_dict_from_aweme(
    aweme: dict[str, Any],
    analyze_result: dict[str, Any],
    niche_id: int,
) -> dict[str, Any]:
    """Synthesise a corpus-row-shaped dict from a fresh aweme + Gemini
    analysis so the downstream synth + response builders work unchanged.

    The on-demand path never persists this row — it just needs the same
    keys ``_response_from_diagnostics_row`` + ``_call_win_gemini`` /
    ``_call_flop_gemini`` + ``build_kpis`` read from a corpus row.
    """
    from getviews_pipeline import ensemble

    metadata = ensemble.parse_metadata(aweme)
    metrics = metadata.metrics
    handle = metadata.author.username if metadata.author else ""
    video_id = str(aweme.get("aweme_id", "") or metadata.video_id or "")

    create_time = aweme.get("create_time") or aweme.get("createTime")
    created_iso: str | None = None
    if isinstance(create_time, (int, float)):
        try:
            created_iso = datetime.fromtimestamp(int(create_time), tz=UTC).isoformat()
        except (OSError, ValueError, OverflowError):
            created_iso = None

    views = int(metrics.views or 0)
    saves = int(metrics.bookmarks or 0)
    save_rate = saves / max(views, 1) if views > 0 else 0.0

    return {
        "video_id": video_id,
        "creator_handle": handle,
        "views": views,
        "likes": int(metrics.likes or 0),
        "comments": int(metrics.comments or 0),
        "shares": int(metrics.shares or 0),
        "saves": saves,
        "save_rate": save_rate,
        "engagement_rate": float(metadata.engagement_rate or 0.0),
        "thumbnail_url": metadata.thumbnail_url,
        "created_at": created_iso,
        "niche_id": niche_id,
        # The Gemini-driven analysis dict — same shape as a corpus row's
        # analysis_json. Drives KPI/segment/hook decomposition downstream.
        "analysis_json": analyze_result.get("analysis") or {},
        # No corpus baseline → assume 1.0 multiplier so retention modeling
        # falls back to the niche median curve without breakout skew.
        "breakout_multiplier": 1.0,
        "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{video_id}"
        if handle and video_id
        else "",
    }


async def _classify_niche_id_async(service_sb: Any, aweme: dict[str, Any]) -> int:
    """Best-effort niche_id from hashtags.

    Falls back to ``0`` when no hashtags match (the FE's ``winners_sample_size``
    null-fallback already renders "Đang xây dựng pool" copy in that case,
    so the user still gets a useful analysis without a niche cohort).
    """
    from getviews_pipeline import ensemble
    from getviews_pipeline.hashtag_niche_map import classify_from_hashtags

    try:
        meta = ensemble.parse_metadata(aweme)
        nid = await classify_from_hashtags(meta.hashtags, service_sb)
        return int(nid) if nid else 0
    except Exception as exc:  # noqa: BLE001 — niche is best-effort, never fatal
        logger.warning(
            "[video_analyze_on_demand] niche classify failed (continuing with 0): %s", exc,
        )
        return 0


async def _fetch_and_analyze_async(tiktok_url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch the aweme via EnsembleData + run Gemini analysis. Returns
    ``(aweme, analyze_result)``. Wrapped so the sync entry point can
    drive both steps under a single ``asyncio.run``."""
    from getviews_pipeline import ensemble
    from getviews_pipeline.analysis_core import analyze_aweme

    aweme = await ensemble.fetch_post_info(tiktok_url)
    analyze_result = await analyze_aweme(aweme, include_diagnosis=False)
    return aweme, analyze_result


def run_video_analyze_on_demand(
    service_sb: Any,
    user_sb: Any,
    *,
    tiktok_url: str,
    mode: Literal["win", "flop"] | None = None,
) -> dict[str, Any]:
    """Sync pipeline for URLs not yet in ``video_corpus``.

    Mirrors the corpus-row branch of ``run_video_analyze_pipeline`` but:
      • Never reads or writes ``video_corpus`` / ``video_diagnostics``.
      • Skips sidecar fetches (``thumbnail_analysis`` + ``comment_radar``
        are corpus-only — no row to attach them to).
      • Best-effort niche resolution via hashtag classifier; when nothing
        matches, ``niche_id=0`` and ``niche_meta`` falls back to the same
        empty-pool copy the existing screen renders for sparse niches.

    Composer wiring (Studio → ``/app/video?url=…``) routes URL pastes
    through ``/video/analyze``; when ``_resolve_video_id`` raises
    ``"Không tìm thấy video trong corpus cho URL này"``, the router
    falls through to this function so the user gets a working analysis
    instead of a 404 dead-end. Result is flagged ``source: "on_demand"``
    so the FE can show a subtle "phân tích trực tiếp, không lưu corpus"
    hint without re-architecting the response shape.
    """
    aweme, analyze_result = asyncio.run(_fetch_and_analyze_async(tiktok_url))

    if "error" in analyze_result or "analysis" not in analyze_result:
        # Gemini choked on the video; surface as a 500-class error rather
        # than masking it as "not found". Caller maps to HTTP 500.
        err = str(analyze_result.get("error") or "Phân tích video thất bại")
        raise RuntimeError(err)

    niche_id = asyncio.run(_classify_niche_id_async(service_sb, aweme))
    video = _build_video_dict_from_aweme(aweme, analyze_result, niche_id)
    vid = video["video_id"]
    if not vid:
        raise ValueError("Aweme thiếu video_id — không phân tích được")

    analysis = video["analysis_json"]
    dur = video_duration_sec(analysis)

    niche_intel = fetch_niche_intelligence_sync(user_sb, niche_id) if niche_id else None
    default_niche_meta = {
        "avg_views": 0,
        "avg_retention": 0.5,
        "avg_ctr": 0.04,
        "sample_size": 0,
        "winners_sample_size": None,
    }

    if mode in ("win", "flop"):
        mode_resolved: Literal["win", "flop"] = mode
    else:
        mode_resolved = "flop" if is_flop_mode(video, niche_intel) else "win"

    bench_payload = build_niche_benchmark_payload(
        niche_intel,
        niche_id=niche_id,
        duration_sec=max(dur, 5.0),
        user_sb=user_sb,
    )
    niche_benchmark = bench_payload["niche_benchmark_curve"]
    niche_meta = (
        bench_payload["niche_meta"]
        if bench_payload.get("niche_meta") is not None
        else default_niche_meta
    )
    rs = bench_payload.get("retention_source") or "modeled"
    retention_source: Literal["real", "modeled"] = "real" if rs == "real" else "modeled"

    niche_label_resolved = _resolve_niche_label(user_sb, niche_id) if niche_id else ""
    gemini_niche_label = niche_label_resolved or "unknown"

    bm = float(video.get("breakout_multiplier") or 1.0)
    retention_user = model_retention_curve(
        max(dur, 5.0),
        niche_median_retention=float(niche_meta["avg_retention"]),
        breakout_multiplier=bm,
        n_points=20,
    )

    segments = decompose_segments(analysis)
    hook_cards = extract_hook_phases(analysis)

    if mode_resolved == "win":
        llm = _call_win_gemini(video=video, analysis=analysis, niche_label=gemini_niche_label)
        for i, body in enumerate(llm.hook_bodies[:3]):
            if i < len(hook_cards):
                hook_cards[i]["body"] = body
        lessons = [x.model_dump() for x in llm.lessons]
        headline: Any = llm.analysis_headline
        subtext = llm.analysis_subtext
        flop_issues: list[dict[str, Any]] | None = None
        projected: int | None = None
    else:
        llm_flop = _call_flop_gemini(
            video=video, analysis=analysis, niche_label=gemini_niche_label, niche_row=niche_intel,
        )
        headline = llm_flop.analysis_headline.model_dump_json()
        subtext = None
        lessons = []
        flop_issues = [x.model_dump() for x in llm_flop.flop_issues]
        projected = projected_views_heuristic(
            int(video.get("views") or 0),
            int(niche_meta["avg_views"] or 0),
            flop_issues,
        )

    diag_synth = {
        "video_id": vid,
        "analysis_headline": headline,
        "analysis_subtext": subtext,
        "lessons": lessons,
        "hook_phases": hook_cards,
        "segments": segments,
        "flop_issues": flop_issues,
        "retention_curve": retention_user,
        "niche_benchmark_curve": niche_benchmark,
        "computed_at": datetime.now(UTC).isoformat(),
    }

    out = _response_from_diagnostics_row(
        video,
        diag_synth,
        mode=mode_resolved,
        niche_meta=niche_meta,
        niche_benchmark=niche_benchmark,
        retention_user=retention_user,
        niche_label=niche_label_resolved,
        retention_source=retention_source,
    )
    if projected is not None:
        out["projected_views"] = projected
    # Flag the response so the FE can render a subtle "phân tích trực tiếp"
    # badge — corpus rows don't set this, so the FE only highlights when
    # explicitly truthy.
    out["source"] = "on_demand"
    return out
