"""P1-9: Trending This Week — Gemini-backed cards from signal_grades + corpus."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from google.genai import types

from getviews_pipeline.config import (
    GEMINI_KNOWLEDGE_FALLBACKS,
    GEMINI_KNOWLEDGE_MODEL,
    GEMINI_TEMPERATURE,
)
from getviews_pipeline.gemini import (
    _generate_content_models,
    _parse_json_object,
    _response_text,
)

logger = logging.getLogger(__name__)

_SIGNAL_ORDER = {"rising": 0, "early": 1, "stable": 2, "declining": 3}

_TRENDING_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": ["title", "description"],
}

_GEMINI_SEM = asyncio.Semaphore(4)


@dataclass
class TrendingCardsResult:
    cards_written: int = 0
    niches_processed: int = 0
    errors: list[str] = field(default_factory=list)


def _week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _format_vn_int(n: int) -> str:
    s = str(n)
    parts: list[str] = []
    while len(s) > 3:
        parts.insert(0, s[-3:])
        s = s[:-3]
    if s:
        parts.insert(0, s)
    return ".".join(parts)


def _sync_delete_week(client: Any, week_of: str) -> None:
    client.table("trending_cards").delete().eq("week_of", week_of).execute()


def _sync_fetch_niches(client: Any) -> list[dict[str, Any]]:
    res = (
        client.table("niche_taxonomy")
        .select("id, name_en, name_vn, signal_hashtags")
        .execute()
    )
    return res.data or []


def _sync_latest_signal_rows(client: Any, niche_id: int) -> list[dict[str, Any]]:
    w = (
        client.table("signal_grades")
        .select("week_start")
        .eq("niche_id", niche_id)
        .order("week_start", desc=True)
        .limit(1)
        .execute()
    )
    rows = w.data or []
    if not rows:
        return []
    latest = rows[0]["week_start"]
    r = (
        client.table("signal_grades")
        .select("hook_type, signal")
        .eq("niche_id", niche_id)
        .eq("week_start", latest)
        .execute()
    )
    raw = r.data or []
    raw.sort(
        key=lambda x: (
            _SIGNAL_ORDER.get(str(x.get("signal")), 99),
            str(x.get("hook_type") or ""),
        )
    )
    return raw[:5]


def _sync_top_videos(
    client: Any,
    niche_id: int,
    hook_type: str,
    since_iso: str,
) -> list[dict[str, Any]]:
    """Return top breakout videos with content fields for Gemini context."""
    res = (
        client.table("video_corpus")
        .select("video_id, hook_phrase, content_format, views, breakout_multiplier")
        .eq("niche_id", niche_id)
        .eq("hook_type", hook_type)
        .gte("indexed_at", since_iso)
        .order("breakout_multiplier", desc=True)
        .limit(48)
        .execute()
    )
    out: list[dict[str, Any]] = []
    for row in res.data or []:
        if row.get("breakout_multiplier") is None:
            continue
        if row.get("video_id"):
            out.append({
                "video_id": str(row["video_id"]),
                "hook_phrase": str(row.get("hook_phrase") or ""),
                "content_format": str(row.get("content_format") or ""),
                "views": int(row.get("views") or 0),
            })
        if len(out) >= 12:
            break
    return out


def _call_gemini_trending_card(
    niche_vn: str,
    niche_en: str,
    hook_type: str,
    signal: str,
    video_data: list[dict[str, Any]],
) -> tuple[str, str] | None:
    # Build the video examples block — top 5 by position (already sorted by breakout)
    examples_lines: list[str] = []
    for i, v in enumerate(video_data[:5], 1):
        hook = v["hook_phrase"] or "(không có hook text)"
        fmt = v["content_format"] or "—"
        views_str = _format_vn_int(v["views"]) if v["views"] else "—"
        examples_lines.append(f'{i}. Hook: "{hook}" | Format: {fmt} | {views_str} views')
    examples_block = "\n".join(examples_lines) if examples_lines else "(không có dữ liệu)"

    n_str = _format_vn_int(len(video_data)) if video_data else "0"
    prompt = f"""Bạn là chuyên gia phân tích content TikTok Việt Nam. Dựa vào {n_str} video đang bùng nổ trong corpus, hãy đặt tên MỘT execution pattern đang thống trị niche này tuần này.

Video bùng nổ nhất (sắp xếp theo breakout multiplier):
{examples_block}

Ngữ cảnh:
- Niche: {niche_vn} ({niche_en})
- Hook category: {hook_type or "(không rõ)"}
- Tín hiệu: {signal}

Quy tắc:
- title: đặt tên CẤU TRÚC THỰC THI cụ thể, không phải tên niche chung chung, tối đa 50 ký tự.
  Ví dụ tốt: "Hook số liệu shock → reveal sai lầm phổ biến"
  Ví dụ tốt: "POV bí mật insider + CTA so sánh giá"
  Ví dụ xấu: "Video câu hỏi đang hot trong niche skincare tuần này"
- description: 1–2 câu, giọng creator-to-creator, giải thích cách làm theo pattern này.
- description phải có cụm "Chạy vì:" giải thích ngắn gọn tại sao pattern này đang work.
- Dùng "tuần này" (không dùng "7 ngày gần nhất").
- Số đếm dùng dấu chấm ngàn kiểu Việt Nam (ví dụ 1.200).

Chỉ trả về JSON, không markdown."""

    cfg = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        response_mime_type="application/json",
        response_json_schema=_TRENDING_JSON_SCHEMA,
        max_output_tokens=512,
    )
    response = _generate_content_models(
        [prompt],
        primary_model=GEMINI_KNOWLEDGE_MODEL,
        fallbacks=GEMINI_KNOWLEDGE_FALLBACKS,
        config=cfg,
    )
    text = _response_text(response)
    if not text.strip():
        return None
    try:
        data = _parse_json_object(text)
    except Exception as e:
        logger.warning("trending_cards JSON parse failed: %s", e)
        return None
    title = str(data.get("title", "")).strip()
    desc = str(data.get("description", "")).strip()
    if not title or not desc:
        return None
    if len(title) > 50:
        title = title[:50].rstrip()
    return title, desc


async def _gemini_with_sem(
    niche_vn: str,
    niche_en: str,
    hook_type: str,
    signal: str,
    video_data: list[dict[str, Any]],
) -> tuple[str, str] | None:
    async with _GEMINI_SEM:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: _call_gemini_trending_card(
                niche_vn, niche_en, hook_type, signal, video_data
            ),
        )


def _build_corpus_cite(name_vn: str, n: int) -> str:
    if n <= 0:
        return f"{name_vn} · chưa có video corpus tuần này cho hook này"
    num = _format_vn_int(n)
    return f"{name_vn} · {num} video nổi bật tuần này trong corpus"


async def _process_niche(
    client: Any,
    niche: dict[str, Any],
    week_of: date,
    since_iso: str,
) -> tuple[int, list[str]]:
    errors: list[str] = []
    nid = int(niche["id"])
    name_vn = str(niche.get("name_vn") or "")
    name_en = str(niche.get("name_en") or "")
    rows = await asyncio.get_event_loop().run_in_executor(
        None, _sync_latest_signal_rows, client, nid
    )
    if not rows:
        return 0, [f"niche {nid}: không có signal_grades"]

    written = 0
    for row in rows:
        hook_type = str(row.get("hook_type") or "")
        sig = str(row.get("signal") or "stable")
        if sig not in ("rising", "early", "stable", "declining"):
            sig = "stable"

        video_dicts = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda h=hook_type: _sync_top_videos(client, nid, h, since_iso),
        )
        if not video_dicts:
            errors.append(f"niche {nid} hook {hook_type}: không có video corpus 7 ngày")
            continue

        vid_ids = [v["video_id"] for v in video_dicts]
        gen = await _gemini_with_sem(name_vn, name_en, hook_type, sig, video_dicts)
        if not gen:
            errors.append(f"niche {nid} hook {hook_type}: Gemini trống hoặc lỗi parse")
            continue
        title, description = gen
        cite = _build_corpus_cite(name_vn, len(video_dicts))
        payload = {
            "niche_id": nid,
            "title": title,
            "description": description,
            "signal": sig,
            "hook_type": hook_type or None,
            "video_ids": vid_ids,
            "corpus_cite": cite,
            "week_of": week_of.isoformat(),
        }
        try:
            ins = client.table("trending_cards").insert(payload).execute()
            if ins.data:
                written += 1
        except Exception as exc:
            errors.append(f"niche {nid} insert: {exc}")

    return written, errors


async def run_trending_cards(client: Any | None = None) -> TrendingCardsResult:
    """Generate trending_cards for the current ISO week (Monday boundary)."""
    result = TrendingCardsResult()
    loop = asyncio.get_event_loop()

    try:
        if client is None:
            try:
                from getviews_pipeline.supabase_client import get_service_client

                client = get_service_client()
            except Exception as exc:
                result.errors.append(str(exc))
                return result

        today = date.today()
        week_of = _week_start_monday(today)
        week_iso = week_of.isoformat()
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)
        since_iso = since_dt.isoformat()

        try:
            await loop.run_in_executor(None, _sync_delete_week, client, week_iso)
        except Exception as exc:
            result.errors.append(f"xóa tuần: {exc}")
            return result

        try:
            niches = await loop.run_in_executor(None, _sync_fetch_niches, client)
        except Exception as exc:
            result.errors.append(f"niche_taxonomy: {exc}")
            return result

        async def _one(niche: dict[str, Any]) -> tuple[int, list[str]]:
            try:
                return await _process_niche(client, niche, week_of, since_iso)
            except Exception as exc:
                return 0, [f"niche {niche.get('id')}: {exc}"]

        gathered = await asyncio.gather(*[_one(n) for n in niches])
        for w, errs in gathered:
            result.cards_written += w
            result.errors.extend(errs)

        result.niches_processed = len(niches)
        return result
    except Exception as exc:
        result.errors.append(f"trending_cards: {exc}")
        return result
