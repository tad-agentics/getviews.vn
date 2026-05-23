from __future__ import annotations

import statistics

from getviews_pipeline.signals.base import Evidence, Signal


def extract_channel_video_vs_eligible_peers_signal(ctx: dict) -> list[Signal]:
    """P2 — video hiện tại underperform vs reference_eligible peers."""
    us = ctx.get("user_stats") if isinstance(ctx.get("user_stats"), dict) else {}
    views = int(us.get("views") or 0)
    if views <= 0:
        return []

    refs = ctx.get("reference_videos") or []
    if not isinstance(refs, list):
        return []
    eligible_views: list[int] = []
    for row in refs:
        if not isinstance(row, dict):
            continue
        if row.get("reference_eligible") is False:
            continue
        try:
            eligible_views.append(int(row.get("views") or 0))
        except (TypeError, ValueError):
            continue
    if len(eligible_views) < 2:
        return []

    peer_med = float(statistics.median(eligible_views))
    if peer_med <= 0 or views >= peer_med * 0.8:
        return []

    return [
        Signal(
            id="channel_video_vs_eligible_peers",
            section_id="channel_pattern",
            taxonomy_ref="§channel",
            salience=0.63,
            claim=(
                f"Video {views:,} view dưới median ~{peer_med:,.0f} của "
                f"{len(eligible_views)} peer reference_eligible — lệch cohort organic-shaped."
            ),
            evidence=[
                Evidence(
                    type="channel_field",
                    quote=f"views={views} peer_median={peer_med:.0f} n_peers={len(eligible_views)}",
                    location="user_stats.views+reference_videos",
                )
            ],
            suggested_fix="So hook/format với peer eligible; tránh copy video suspect_medium làm anchor.",
        )
    ]


def extract_channel_signals(ctx: dict) -> list[Signal]:
    ch = ctx.get("channel_context") or {}
    if not isinstance(ch, dict) or not ch.get("available"):
        out: list[Signal] = []
        out.extend(extract_channel_video_vs_eligible_peers_signal(ctx))
        return out

    sample = int(ch.get("sample_size") or 0)
    med = ch.get("median_views")
    out: list[Signal] = []
    if sample >= 3 and med is not None:
        out.append(
            Signal(
                id="channel_baseline_available",
                section_id="channel_pattern",
                taxonomy_ref="§channel",
                salience=0.56,
                claim="Đủ video trong kho để so baseline kênh với video hiện tại.",
                evidence=[
                    Evidence(
                        type="channel_field",
                        quote=f"sample_size={sample} median_views={med}",
                        location="channel_context",
                    )
                ],
                suggested_fix=None,
            )
        )

    tier = str(ctx.get("performance_tier") or "unknown").lower()
    if tier == "flop" and sample >= 3:
        out.append(
            Signal(
                id="channel_pattern_break_risk",
                section_id="channel_pattern",
                taxonomy_ref="§channel",
                salience=0.60,
                claim="Tier flop với baseline kênh có sẵn — cần kiểm tra lệch format/hook so với hit gần đây.",
                evidence=[
                    Evidence(
                        type="channel_field",
                        quote=f"performance_tier={tier}",
                        location="ctx",
                    )
                ],
                suggested_fix="Lệch so với top 2–3 video views của kênh cần được nêu rõ trong bài.",
            )
        )

    out.extend(extract_channel_video_vs_eligible_peers_signal(ctx))
    return out
