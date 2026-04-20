"""Phase C.3.2 — deterministic aggregators for Ideas reports.

Same shape as ``report_pattern_compute.py`` — DB reads + rank / shape helpers.
Gemini-bounded narrative is optional and lives in ``report_ideas_gemini.py``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from getviews_pipeline.report_types import (
    ActionCardPayload,
    IdeaBlockPayload,
)
from getviews_pipeline.script_data import HOOK_TYPE_PATTERN_VI, latest_hook_effectiveness_rows

logger = logging.getLogger(__name__)


# ── Shared helpers (mirror Pattern) ──────────────────────────────────────────


def _pattern_label(hook_type: str) -> str:
    key = (hook_type or "").strip().lower().replace("-", "_")
    return HOOK_TYPE_PATTERN_VI.get(key, (hook_type or "hook").replace("_", " ").title() or "Hook")


def _prereq_chips(hook_type: str) -> list[str]:
    key = (hook_type or "").strip().lower().replace("-", "_")
    defaults: dict[str, list[str]] = {
        "question": ["Câu hỏi trong 0.5s đầu", "Nhìn thẳng camera"],
        "bold_claim": ["Claim trong 1s", "Chữ lớn trên màn hình"],
        "shock_stat": ["Số liệu nguồn rõ", "Cut nhanh sau stat"],
        "story_open": ["Hook cảm xúc 2–4s", "Bối cảnh nhận diện được"],
        "curiosity_gap": ["Khoảng trống ở 3s đầu", "Payoff trước giây 12"],
        "social_proof": ["Bằng chứng xã hội 1–3s", "UGC / testimonial rõ"],
        "how_to": ["Bước 1 ngay đầu", "Chữ overlay đồng bộ"],
        "pain_point": ["Gọi đúng pain 1s đầu", "Giải pháp preview nhỏ"],
        "trend_hijack": ["Trend audio khớp niche", "Twist trong 2s"],
    }
    return defaults.get(key, ["Ổn định khung 9:16", "Audio rõ trong 2s đầu"])


_TAG_BY_HOOK: dict[str, str] = {
    "question": "question",
    "bold_claim": "bold_claim",
    "shock_stat": "stat",
    "story_open": "story",
    "curiosity_gap": "curiosity_gap",
    "social_proof": "testimonial",
    "how_to": "how_to",
    "pain_point": "pain_point",
    "trend_hijack": "trend_hijack",
}


def _tag_for_hook(hook_type: str) -> str:
    key = (hook_type or "").strip().lower().replace("-", "_")
    return _TAG_BY_HOOK.get(key, "listicle")


def _style_for_hook(hook_type: str) -> str:
    key = (hook_type or "").strip().lower().replace("-", "_")
    mapping = {
        "question": "voice-led",
        "bold_claim": "handheld",
        "shock_stat": "screen-record",
        "story_open": "handheld",
        "curiosity_gap": "voice-led",
        "social_proof": "handheld",
        "how_to": "screen-record",
        "pain_point": "voice-led",
        "trend_hijack": "desk",
    }
    return mapping.get(key, "handheld")


def _evidence_ids_for_hook(corpus_rows: list[dict[str, Any]], hook_type: str, *, limit: int) -> list[str]:
    matched = [x for x in corpus_rows if (x.get("hook_type") or "") == hook_type]
    matched.sort(key=lambda x: int(x.get("views") or 0), reverse=True)
    return [str(x.get("video_id")) for x in matched[:limit] if x.get("video_id")]


def _creator_count(corpus_rows: list[dict[str, Any]], hook_type: str) -> int:
    return len({str(x.get("creator_handle") or "") for x in corpus_rows if (x.get("hook_type") or "") == hook_type})


def _fmt_pct(x: float) -> str:
    return f"{int(round(x * 100))}%"


def _score_row(r: dict[str, Any]) -> float:
    av = float(r.get("avg_views") or 0)
    ret = float(r.get("avg_completion_rate") or 0)
    return av * max(ret, 0.05)


# ── Rank + compute helpers ──────────────────────────────────────────────────


def rank_hooks_for_ideas(he_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same ranking as Pattern — Ideas consumes the top 5 hook families by
    ``avg_views × avg_completion_rate``."""
    scored = [(_score_row(r), r) for r in he_rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]


def _retention_range(ret: float) -> tuple[str, str]:
    """Display band ± ~8 pp either side of observed completion, capped 0–99."""
    mid = max(0.0, min(0.99, ret))
    lo = max(0.0, mid - 0.08)
    hi = min(0.99, mid + 0.08)
    return f"{_fmt_pct(lo)}–{_fmt_pct(hi)}", _fmt_pct(mid)


def compute_ideas_blocks(
    ranked_hooks: list[dict[str, Any]],
    corpus_rows: list[dict[str, Any]],
    baseline_views: float,  # noqa: ARG001 — reserved for future Gemini grounding
) -> list[IdeaBlockPayload]:
    """Build up to 5 IdeaBlocks from the top-ranked hook families (C.3.2)."""
    out: list[IdeaBlockPayload] = []
    for i, r in enumerate(ranked_hooks[:5]):
        ht = str(r.get("hook_type") or "")
        ret = float(r.get("avg_completion_rate") or 0)
        uses = int(r.get("sample_size") or 0)
        creators = _creator_count(corpus_rows, ht)
        mid_pct, _range_mid = _retention_range(ret)
        ev_ids = _evidence_ids_for_hook(corpus_rows, ht, limit=2)
        label = _pattern_label(ht)
        block = IdeaBlockPayload(
            id=f"{i + 1:02d}",
            title=label,
            tag=_tag_for_hook(ht),
            angle=(
                f"Hướng {label.lower()} cho tuần tới: giữ hook ≤ 1.4s, payoff "
                f"cụ thể trong 12s đầu."
            )[:240],
            why_works=(
                f"Trong corpus 7–14 ngày, {label} đạt retention {_fmt_pct(ret)} "
                f"trên {uses} video từ {creators} creator."
            ),
            evidence_video_ids=ev_ids,
            hook=f"{label}: câu mở đi trực tiếp vào pain/curiosity."[:100],
            slides=[
                {"step": 1, "body": "Hook ≤ 1.4s — câu mở + mặt / chữ overlay."},
                {"step": 2, "body": "Giây 2–5 — nêu claim/pain cụ thể, không vòng vo."},
                {"step": 3, "body": "Giây 5–15 — demo/chứng cứ trực quan."},
                {"step": 4, "body": "Giây 15–30 — 2 chi tiết bổ sung + nhịp cắt nhanh."},
                {"step": 5, "body": "Giây 30–45 — twist nhỏ hoặc số liệu đinh."},
                {"step": 6, "body": "CTA hỏi ngược 1 câu, không dùng 'follow'."},
            ],
            metric={"label": "RETENTION DỰ KIẾN", "value": mid_pct, "range": _retention_range(ret)[0]},
            prerequisites=_prereq_chips(ht),
            confidence={"sample_size": uses, "creators": creators},
            style=_style_for_hook(ht),
        )
        out.append(block)
    return out


def compute_style_cards(
    style_distribution: list[dict[str, Any]] | None,
    *,
    n: int = 5,
    fallback_niche: str = "Niche",
) -> list[dict[str, Any]]:
    """5 style cards. Uses ``niche_taxonomy.style_distribution`` when populated
    (C.3.1 migration added the column); otherwise falls back to a generic set
    so the section always renders the expected 5 cards."""
    sd = style_distribution or []
    cards: list[dict[str, Any]] = []
    for i, row in enumerate(sd[:n]):
        name = str(row.get("name") or row.get("style") or f"Style {i + 1}")
        desc = str(row.get("desc") or row.get("description") or "Phong cách quay đặc trưng của ngách.")
        paired = row.get("paired_ideas") or [f"#{i + 1}"]
        if not isinstance(paired, list):
            paired = [f"#{i + 1}"]
        cards.append({"id": str(i + 1), "name": name, "desc": desc, "paired_ideas": paired})

    defaults = [
        ("Handheld P2P", "Cầm tay, mắt nhìn camera, cắt nhanh mỗi 2–3s.", ["#1", "#3"]),
        ("Screen record overlay", "Màn hình + text bản địa hóa, speed ×1.5–×2.", ["#2"]),
        ("Before / after", "So sánh hai trạng thái, 3–5s mỗi bên.", ["#4"]),
        ("Desk demo", "Bàn làm việc gọn gàng, ánh sáng 45°.", ["#5"]),
        ("Voice-led", "Dựa vào voiceover, B-roll cắt theo nhịp.", ["#1", "#4"]),
    ]
    while len(cards) < n:
        d = defaults[len(cards) % len(defaults)]
        cards.append(
            {
                "id": str(len(cards) + 1),
                "name": d[0],
                "desc": d[1] + f" (gợi ý mặc định cho {fallback_niche}.)" if not sd else d[1],
                "paired_ideas": d[2],
            }
        )
    return cards


def compute_stop_doing(
    he_rows: list[dict[str, Any]],
    baseline_views: float,  # noqa: ARG001 — reserved
) -> list[dict[str, str]]:
    """Bottom-5 hook families by retention, with Gemini-free default copy.

    Returns ``[]`` only when corpus is too thin to identify 3+ under-performers;
    ``IdeasBody`` hides the section on an empty list (plan §2.2 empty state).
    """
    eligible = [r for r in he_rows if int(r.get("sample_size") or 0) >= 5]
    if len(eligible) < 3:
        return []
    ranked = sorted(eligible, key=lambda x: float(x.get("avg_completion_rate") or 0))
    bottom = ranked[:5]
    out: list[dict[str, str]] = []
    for r in bottom:
        ht = str(r.get("hook_type") or "")
        label = _pattern_label(ht)
        ret = float(r.get("avg_completion_rate") or 0)
        why = (
            f"{label} đang giữ retention chỉ {_fmt_pct(ret)} — thấp hơn đáng kể "
            f"so với nhóm hook đang thắng."
        )
        fix = (
            f"Thay {label.lower()} bằng hook direct-testimonial hoặc curiosity "
            f"gap trong 7 ngày test tiếp theo."
        )
        out.append({"bad": label, "why": why, "fix": fix})
    return out


def static_ideas_action_cards(
    baseline_views: float,
    *,
    top_idea_hook: str | None = None,
) -> list[ActionCardPayload]:
    """Two CTAs: open Xưởng Viết with idea #1 + save 5 ideas into schedule."""
    low = max(1000, int(baseline_views * 0.9))
    high = max(low + 500, int(baseline_views * 1.35))
    mid = int(baseline_views) if baseline_views > 0 else 5000
    sub_primary = (
        f"Dùng hook ‘{top_idea_hook}’" if top_idea_hook else "Draft từ ý tưởng #1"
    )
    return [
        ActionCardPayload(
            icon="sparkles",
            title="Mở Xưởng Viết với ý #1",
            sub=sub_primary[:80],
            cta="Mở",
            primary=True,
            route="/app/script",
            forecast={"expected_range": f"{low//1000}K–{high//1000}K", "baseline": f"{mid//1000}K"},
        ),
        ActionCardPayload(
            icon="save",
            title="Lưu cả 5 ý tưởng",
            sub="Đưa vào lịch quay 7 ngày",
            cta="Lưu",
            route="/app/history",
            forecast={"expected_range": "—", "baseline": "—"},
        ),
    ]


# ── DB loader ────────────────────────────────────────────────────────────────


def fetch_corpus_window(sb: Any, niche_id: int, days: int, *, limit: int = 2500) -> list[dict[str, Any]]:
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        res = (
            sb.table("video_corpus")
            .select(
                "video_id, creator_handle, views, hook_type, indexed_at, created_at, "
                "engagement_rate, video_duration, analysis_json, caption, thumbnail_url"
            )
            .eq("niche_id", niche_id)
            .gte("indexed_at", cutoff)
            .order("views", desc=True)
            .limit(limit)
            .execute()
        )
        return list(res.data or [])
    except Exception as exc:
        logger.warning("[ideas] corpus fetch failed: %s", exc)
        return []


def load_ideas_inputs(sb: Any, niche_id: int, window_days: int) -> dict[str, Any] | None:
    """Load niche label, intelligence row, hook_effectiveness, corpus slice,
    plus ``style_distribution`` from ``niche_taxonomy`` (migration
    20260430000004 added the column)."""
    try:
        nt = (
            sb.table("niche_taxonomy")
            .select("name_vn, name_en, style_distribution")
            .eq("id", niche_id)
            .maybe_single()
            .execute()
        )
        row = nt.data or {}
        label = str(row.get("name_vn") or row.get("name_en") or f"Niche {niche_id}")
        style_dist = row.get("style_distribution") or []

        ni_res = sb.table("niche_intelligence").select("*").eq("niche_id", niche_id).maybe_single().execute()
        ni = ni_res.data or {}

        he_res = (
            sb.table("hook_effectiveness")
            .select(
                "hook_type, avg_views, avg_completion_rate, sample_size, trend_direction, computed_at"
            )
            .eq("niche_id", niche_id)
            .order("computed_at", desc=True)
            .limit(300)
            .execute()
        )
        he_raw = he_res.data or []
        he_latest = latest_hook_effectiveness_rows(he_raw if isinstance(he_raw, list) else [])

        corpus = fetch_corpus_window(sb, niche_id, max(window_days, 14))

        return {
            "niche_label": label,
            "ni": ni,
            "he_rows": he_latest,
            "corpus": corpus,
            "style_distribution": style_dist,
        }
    except Exception as exc:
        logger.warning("[ideas] load_ideas_inputs failed: %s", exc)
        return None
