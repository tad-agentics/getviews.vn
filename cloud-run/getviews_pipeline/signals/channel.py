from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def extract_channel_signals(ctx: dict) -> list[Signal]:
    ch = ctx.get("channel_context") or {}
    if not isinstance(ch, dict) or not ch.get("available"):
        return []

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

    return out
