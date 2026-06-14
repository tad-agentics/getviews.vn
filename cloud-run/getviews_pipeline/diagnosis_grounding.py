"""Prompt blocks grounding live diagnosis in measured hook lift + comment_radar."""

from __future__ import annotations

import logging
from typing import Any

from getviews_pipeline.claim_tiers import (
    HOOK_EFFECTIVENESS_MIN_PER_BUCKET,
    should_cite_hook_effectiveness,
)
from getviews_pipeline.enum_labels_vi import hook_type_vi, trend_vi

logger = logging.getLogger(__name__)

COMMENT_MIN_SAMPLE = 8
_COMMENT_LANGUAGES = frozenset({"vi", "mixed"})


def _user_hook_type(user_analysis: dict[str, Any]) -> str:
    ha = user_analysis.get("hook_analysis")
    if isinstance(ha, dict):
        return str(ha.get("hook_type") or "").strip()
    return ""


def _eligible_hook_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if int(r.get("sample_size") or 0) >= HOOK_EFFECTIVENESS_MIN_PER_BUCKET
    ]


def build_hook_leaderboard_block(
    rows: list[dict[str, Any]] | None,
    *,
    user_hook_type: str,
    class_label: str,
) -> tuple[str, dict[str, Any]]:
    """Return (prompt block, telemetry fragment). Empty block when gated."""
    telemetry: dict[str, Any] = {
        "hook_leaderboard_emitted": False,
        "hook_buckets_above_floor": 0,
    }
    if not rows:
        return "", telemetry

    eligible = _eligible_hook_rows(rows)
    total_samples = sum(int(r.get("sample_size") or 0) for r in rows)
    telemetry["hook_buckets_above_floor"] = len(eligible)

    if not should_cite_hook_effectiveness(total_samples) or not eligible:
        return "", telemetry

    ranked = sorted(eligible, key=lambda r: int(r.get("avg_views") or 0), reverse=True)
    top = ranked[0]
    top_hook = str(top.get("hook_type") or "")
    top_views = int(top.get("avg_views") or 0)
    top_n = int(top.get("sample_size") or 0)
    n_class = total_samples

    lines = [
        f"HOOK_LEADERBOARD (ngách: {class_label or '—'}, n_class={n_class}):",
    ]

    user_ht = (user_hook_type or "").strip()
    user_row: dict[str, Any] | None = None
    user_rank: int | None = None
    if user_ht:
        for idx, row in enumerate(ranked, start=1):
            if str(row.get("hook_type") or "") == user_ht:
                user_row = row
                user_rank = idx
                break

    user_above = (
        user_row is not None
        and int(user_row.get("sample_size") or 0) >= HOOK_EFFECTIVENESS_MIN_PER_BUCKET
    )

    if user_above and user_rank is not None and user_row is not None:
        u_views = int(user_row.get("avg_views") or 0)
        u_n = int(user_row.get("sample_size") or 0)
        trend = trend_vi(str(user_row.get("trend_direction") or ""))
        trend_part = f", xu hướng: {trend}" if trend else ""
        lines.append(
            f"- Hook bạn đang dùng: {hook_type_vi(user_ht, default=user_ht)} — "
            f"hạng {user_rank}/{len(ranked)} theo views TB "
            f"(n={u_n}{trend_part})"
        )
        if top_hook and top_hook != user_ht and top_views > 0 and u_views > 0:
            mult = max(1.0, round(top_views / u_views, 1))
            lines.append(
                f"- Hook mạnh nhất ngách: {hook_type_vi(top_hook, default=top_hook)} — "
                f"views TB cao hơn ~{mult}× (n={top_n})"
            )
    elif top_hook and top_n >= HOOK_EFFECTIVENESS_MIN_PER_BUCKET:
        lines.append(
            f"- Hook mạnh nhất ngách: {hook_type_vi(top_hook, default=top_hook)} — "
            f"views TB n={top_n}"
        )

    if len(lines) <= 1:
        return "", telemetry

    lines.append(
        "Chỉ dùng số liệu HOOK_LEADERBOARD nếu khối này xuất hiện; "
        "KHÔNG tự bịa hạng/bội số."
    )
    telemetry["hook_leaderboard_emitted"] = True
    return "\n".join(lines), telemetry


def build_comment_signal_block(radar: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """Return (prompt block, telemetry fragment). Empty when gated."""
    telemetry: dict[str, Any] = {
        "comment_block_emitted": False,
        "comment_sampled": 0,
    }
    if not isinstance(radar, dict):
        return "", telemetry

    sampled = int(radar.get("sampled") or 0)
    telemetry["comment_sampled"] = sampled
    language = str(radar.get("language") or "").lower()
    if sampled < COMMENT_MIN_SAMPLE or language not in _COMMENT_LANGUAGES:
        return "", telemetry

    sentiment = radar.get("sentiment") if isinstance(radar.get("sentiment"), dict) else {}
    purchase = (
        radar.get("purchase_intent") if isinstance(radar.get("purchase_intent"), dict) else {}
    )
    pos = float(sentiment.get("positive_pct") or 0)
    neg = float(sentiment.get("negative_pct") or 0)
    questions = int(radar.get("questions_asked") or 0)
    intent_count = int(purchase.get("count") or 0)
    phrases_raw = purchase.get("top_phrases")
    phrases: list[str] = []
    if isinstance(phrases_raw, list):
        phrases = [str(p).strip() for p in phrases_raw if str(p).strip()][:2]

    lines = [
        f"COMMENT_SIGNAL (mẫu {sampled} bình luận):",
        f"- Cảm xúc: tích cực {pos:.0f}%, tiêu cực {neg:.0f}%",
    ]
    if questions > 0:
        lines.append(
            f"- Câu hỏi lặp lại: {questions} (gợi ý nội dung tiếp theo)"
        )
    if intent_count > 0 and phrases:
        quoted = ", ".join(f'"{p}"' for p in phrases)
        lines.append(f"- Ý định mua: {intent_count} — cụm: {quoted}")
    elif intent_count > 0:
        lines.append(f"- Ý định mua: {intent_count}")

    lines.append(
        "COMMENT_SIGNAL phản ánh khán giả thực; nếu questions_asked cao, nêu 1 gợi ý "
        "nội dung tiếp; nếu cảm xúc tiêu cực cao, soi nguyên nhân. "
        "KHÔNG bịa nội dung bình luận."
    )
    telemetry["comment_block_emitted"] = True
    return "\n".join(lines), telemetry


def compute_diagnosis_grounding(
    *,
    hook_effectiveness: list[dict[str, Any]] | None,
    user_analysis: dict[str, Any],
    comment_radar: dict[str, Any] | None,
    class_label: str,
    emit_hook: bool,
    emit_comment: bool,
) -> tuple[str, str, dict[str, Any]]:
    """Build optional prompt blocks + merged telemetry."""
    hook_block, hook_tel = build_hook_leaderboard_block(
        hook_effectiveness,
        user_hook_type=_user_hook_type(user_analysis),
        class_label=class_label,
    )
    comment_block, comment_tel = build_comment_signal_block(comment_radar)
    telemetry = {**hook_tel, **comment_tel}
    telemetry["hook_block_would_emit"] = bool(hook_block)
    telemetry["comment_block_would_emit"] = bool(comment_block)
    return (
        hook_block if emit_hook else "",
        comment_block if emit_comment else "",
        telemetry,
    )


def log_diagnosis_grounding_telemetry(
    telemetry: dict[str, Any],
    *,
    video_id: str | None = None,
) -> None:
    logger.info(
        "[diagnosis_grounding] video_id=%s hook_emitted=%s hook_buckets=%d "
        "hook_would=%s comment_emitted=%s comment_would=%s comment_sampled=%d",
        video_id or "",
        telemetry.get("hook_leaderboard_emitted"),
        telemetry.get("hook_buckets_above_floor", 0),
        telemetry.get("hook_block_would_emit"),
        telemetry.get("comment_block_emitted"),
        telemetry.get("comment_block_would_emit"),
        telemetry.get("comment_sampled", 0),
    )


__all__ = [
    "COMMENT_MIN_SAMPLE",
    "build_comment_signal_block",
    "build_hook_leaderboard_block",
    "compute_diagnosis_grounding",
    "log_diagnosis_grounding_telemetry",
]
