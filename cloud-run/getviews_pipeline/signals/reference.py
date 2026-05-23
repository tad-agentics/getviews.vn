from __future__ import annotations

from getviews_pipeline.signals.base import Evidence, Signal


def extract_niche_format_underrepresented_signal(ctx: dict) -> list[Signal]:
    fmt = str(ctx.get("content_format") or "").strip().lower().replace("-", "_")
    if not fmt:
        return []

    nm = ctx.get("niche_meta") or {}
    if not isinstance(nm, dict):
        return []
    dist = nm.get("format_distribution")
    if not isinstance(dist, dict) or not dist:
        return []
    sample = int(nm.get("sample_size") or 0)
    if sample < 30:
        return []

    norm_dist: dict[str, int] = {
        str(k).strip().lower().replace("-", "_"): int(v or 0)
        for k, v in dist.items()
    }
    fmt_share = norm_dist.get(fmt, 0)
    if fmt_share >= 8:
        return []

    return [
        Signal(
            id="niche_format_underrepresented",
            section_id="niche_pattern",
            taxonomy_ref="§4.8.3",
            salience=0.74,
            claim=(
                f"Format `{fmt}` chỉ ~{fmt_share}% corpus ngách — "
                "có khoảng trống format chưa khai thác nhiều."
            ),
            evidence=[
                Evidence(
                    type="user_analysis_field",
                    quote=f"content_format={fmt} niche_share={fmt_share}%",
                    location="content_format+niche_meta.format_distribution",
                )
            ],
            suggested_fix="Thử biến thể rõ trong format hiếm nếu hook đủ mạnh.",
        )
    ]


def extract_reference_signals(ctx: dict) -> list[Signal]:
    out: list[Signal] = []
    out.extend(extract_niche_format_underrepresented_signal(ctx))

    refs = ctx.get("reference_videos") or []
    if not isinstance(refs, list) or not refs:
        return out

    top = refs[0]
    aid = str(top.get("aweme_id") or top.get("video_id") or "")
    handle = str(top.get("creator_handle") or top.get("handle") or "ref")
    views = int(top.get("views") or 0)

    out.append(
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
    )
    return out
