from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def extract_reference_signals(ctx: dict) -> list[Signal]:
    refs = ctx.get("reference_videos") or []
    if not isinstance(refs, list) or not refs:
        return []

    top = refs[0]
    aid = str(top.get("aweme_id") or top.get("video_id") or "")
    handle = str(top.get("creator_handle") or top.get("handle") or "ref")
    views = int(top.get("views") or 0)

    return [
        Signal(
            id="niche_reference_anchor",
            section_id="niche_pattern",
            taxonomy_ref="§pattern",
            salience=0.58,
            claim="Có video tham chiếu trong ngách để neo pattern hiện tại.",
            evidence=[
                Evidence(
                    type="aweme_id",
                    quote=f"@{handle} {views} views",
                    location=aid or None,
                )
            ],
            suggested_fix=None,
        )
    ]
