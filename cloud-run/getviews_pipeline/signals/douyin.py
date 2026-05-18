"""§8 Douyin origin + migration-fit signals (diagnosis-first Sprint 9)."""

from __future__ import annotations

from typing import Any

from getviews_pipeline.signals.base import Evidence, Signal


def _ua(ctx: dict) -> dict[str, Any]:
    ua = ctx.get("user_analysis")
    return ua if isinstance(ua, dict) else {}


def extract_douyin_origin_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    origin = ua.get("douyin_origin")
    if not isinstance(origin, dict):
        return []
    aid = str(origin.get("douyin_aweme_id") or "").strip()
    if not aid:
        return []
    stage = str(ua.get("vietnam_adoption_stage") or "").strip().lower()
    if stage == "leading_edge":
        sal = 0.7
    elif stage == "mid_curve":
        sal = 0.6
    elif stage == "trailing":
        sal = 0.45
    else:
        sal = 0.5
    lag = origin.get("lag_days")
    return [
        Signal(
            id="douyin_origin_peer",
            section_id="douyin_origin",
            taxonomy_ref="§8",
            salience=sal,
            claim=(
                f"Khớp format hook với clip Douyin tương tự trong kho (aweme {aid}) — "
                f"giai đoạn lan toả VN: {stage or 'chưa xác định'}."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"douyin_aweme_id={aid} lag_days={lag} stage={stage or 'n/a'}",
                    location="douyin_match",
                ),
            ],
            suggested_fix=(
                "Nếu đang ở mid/trailing: làm rõ điểm khác biệt địa phương; nếu leading_edge: "
                "tối ưu execution để không bị copy nhanh."
            ),
        )
    ]


def extract_migration_fit_signal(ctx: dict) -> list[Signal]:
    ua = _ua(ctx)
    if ua.get("migration_fit_assessment") != "poor_fit":
        return []
    origin = ua.get("douyin_origin")
    aid = ""
    if isinstance(origin, dict):
        aid = str(origin.get("douyin_aweme_id") or "").strip()
    return [
        Signal(
            id="douyin_migration_poor_fit",
            section_id="douyin_origin",
            taxonomy_ref="§8",
            salience=0.55,
            claim=(
                "Mức adapt Douyin → VN đánh dấu đỏ — ngữ cảnh hoặc nhịp format khó chuyển "
                "trực tiếp, dễ flop nếu copy máy móc."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"migration_fit_assessment=poor_fit douyin_aweme_id={aid or 'n/a'}",
                    location="douyin_corpus.adapt_level",
                ),
            ],
            suggested_fix=(
                "Việt hoá CTA, giá/sp, và humor địa phương; tránh punchline phụ thuộc văn hoá "
                "Hoa ngữ nếu khán giả VN không có bối cảnh."
            ),
        )
    ]


def extract_douyin_signals(ctx: dict) -> list[Signal]:
    return [*extract_douyin_origin_signal(ctx), *extract_migration_fit_signal(ctx)]
