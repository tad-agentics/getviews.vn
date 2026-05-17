from __future__ import annotations

import re

from getviews_pipeline.signals.base import Evidence, Signal

_GENERIC_HASHTAGS = frozenset(
    {
        "fyp",
        "foryou",
        "foryoupage",
        "viral",
        "trending",
        "xuhuong",
        "tiktok",
        "learnontiktok",
    }
)


def extract_distribution_signals(ctx: dict) -> list[Signal]:
    stats = ctx.get("user_stats") or {}
    caption = str(stats.get("caption") or "").strip()
    cap_len = len(caption)
    tags_raw = str(stats.get("hashtags") or stats.get("hashtag_string") or "")
    tags = [t.lower().lstrip("#") for t in re.findall(r"#?([\wĐđàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]+)", tags_raw, re.UNICODE)]

    out: list[Signal] = []
    if cap_len > 0 and cap_len < 60:
        out.append(
            Signal(
                id="caption_thin",
                section_id="distribution",
                taxonomy_ref="§meta",
                salience=0.72,
                claim=f"Caption chỉ {cap_len} ký tự — mỏng hơn chuẩn discoverability.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote=f"caption_len={cap_len}",
                        location="user_stats.caption",
                    )
                ],
                suggested_fix="Mở rộng caption ≥100 ký tự với từ khóa ngách cụ thể.",
            )
        )

    if tags:
        generic_n = sum(1 for t in tags if t in _GENERIC_HASHTAGS)
        if generic_n >= max(3, len(tags) - 1):
            out.append(
                Signal(
                    id="hashtag_generic_cluster",
                    section_id="distribution",
                    taxonomy_ref="§meta",
                    salience=0.68,
                    claim="Hashtag chủ yếu generic — thuật toán khó phân loại ngách.",
                    evidence=[
                        Evidence(
                            type="user_analysis_field",
                            quote=f"hashtags={tags[:12]}",
                            location="user_stats",
                        )
                    ],
                    suggested_fix="Thay 2–4 hashtag generic bằng hashtag chỉ rõ subniche.",
                )
            )

    music_origin = str(stats.get("music_origin") or "").lower()
    if music_origin == "original":
        out.append(
            Signal(
                id="sound_original",
                section_id="distribution",
                taxonomy_ref="§6",
                salience=0.52,
                claim="Nhạc original — kiểm tra có đang bỏ lỡ sound trending ngách.",
                evidence=[
                    Evidence(
                        type="user_analysis_field",
                        quote="music_origin=original",
                        location="user_stats",
                    )
                ],
                suggested_fix=None,
            )
        )

    return out
