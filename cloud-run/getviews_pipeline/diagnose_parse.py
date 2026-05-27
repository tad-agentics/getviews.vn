from __future__ import annotations

import re
from typing import Any

_VIDEO_SECTION_MARKERS = re.compile(
    r"^=== (diagnosis|compliance|distribution|niche_pattern|channel_pattern|commerce|next_video) ===\s*$",
    re.MULTILINE,
)
_TITLE_RE = re.compile(r"^TITLE:\s*(.+)$", re.MULTILINE)
_EMBED_TILES = re.compile(
    r"<<<EMBEDDED_TILES>>>\s*(.*?)\s*(?=<<<|\Z)", re.DOTALL | re.IGNORECASE
)
_NEXT_CARD = re.compile(
    r"<<<NEXT_VIDEO_CARD>>>\s*(.*?)\s*(?=<<<|\Z)", re.DOTALL | re.IGNORECASE
)


def parse_diagnosis_sections_markdown(narrative: str) -> list[dict[str, Any]]:
    """Split model markdown on === section_id === markers (channel-style)."""
    parts = _VIDEO_SECTION_MARKERS.split(narrative.strip())
    sections: list[dict[str, Any]] = []
    for i in range(1, len(parts), 2):
        section_id = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        title_m = _TITLE_RE.search(body)
        title = title_m.group(1).strip() if title_m else ""
        clean_body = _TITLE_RE.sub("", body, count=1).strip()
        embedded: list[dict[str, Any]] = []
        nt_m = _EMBED_TILES.search(clean_body)
        if nt_m:
            raw = nt_m.group(1).strip()
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                aweme_id = (
                    line.split()[0].replace('"', "").replace(",", "")
                )
                if aweme_id.isdigit():
                    embedded.append({"aweme_id": aweme_id})
            clean_body = clean_body.replace(nt_m.group(0), "").strip()
        next_video: dict[str, Any] | None = None
        nv_m = _NEXT_CARD.search(clean_body)
        if nv_m:
            next_video = {"raw": nv_m.group(1).strip()}
            clean_body = clean_body.replace(nv_m.group(0), "").strip()
        sections.append(
            {
                "section_id": section_id,
                "title": title,
                "text": clean_body,
                "embedded_tiles": embedded,
                "next_video": next_video,
            }
        )
    return sections


_MAX_EMBEDDED_TILES_PER_SECTION = 3


def _format_views_compact_vi(n: int) -> str:
    if n >= 1_000_000:
        label = f"{n / 1_000_000:.1f}M"
        return label.replace(".0M", "M")
    if n >= 1_000:
        label = f"{n / 1_000:.1f}K"
        return label.replace(".0K", "K")
    return str(n)


_SECTION_TILE_NARRATIVE_ANGLE: dict[str, str] = {
    "hook_analysis": "Hãy quan sát kỹ cách video này tối ưu 3 giây đầu (về nhịp cắt cảnh, cách hiện chữ overlay và hình ảnh mở đầu) để học hỏi cách lôi cuốn người lướt ngay lập tức.",
    "diagnosis": "Phân tích cách video này xây dựng format và giữ chân khán giả ổn định xuyên suốt thời lượng để áp dụng các điểm tương đồng vào clip của bạn.",
    "niche_pattern": "Đây là một công thức đang thắng lớn trong ngách. Hãy xem cách họ lặp lại các yếu tố cốt lõi để đưa vào kịch bản tiếp theo của bạn.",
    "distribution": "Tham khảo khung giờ đăng và nhịp cắn xu hướng của video này để tối ưu hóa thời điểm phân phối hiệu quả nhất cho kênh của bạn.",
    "script_structure": "Hãy đối chiếu nhịp phân đoạn, diễn tiến câu chuyện và cách họ chuyển cảnh (transitions) với cấu trúc clip của bạn.",
}

CONTENT_FORMAT_VI: dict[str, str] = {
    "tutorial": "hướng dẫn (tutorial)",
    "review": "đánh giá (review)",
    "haul": "mua sắm (haul)",
    "grwm": "GRWM (chuẩn bị cùng tôi)",
    "vlog": "vlog",
    "before_after": "trước và sau (before/after)",
    "pov": "POV (góc nhìn)",
    "talking_head": "nói trước camera (talking head)",
    "storytime": "kể chuyện",
    "listicle": "danh sách (listicle)",
    "mukbang": "mukbang",
    "recipe": "nấu ăn",
    "comparison": "so sánh",
    "storytelling": "kể chuyện",
    "comedy_skit": "tiểu phẩm hài",
    "outfit_transition": "phối đồ / biến hình (outfit transition)",
    "dance": "nhảy",
    "faceless": "không lộ mặt",
    "highlight": "tóm tắt clip",
    "gameplay": "chơi game",
    "lesson": "bài học",
    "other": "khác",
}


def fallback_tile_narrative_vi(
    tile: dict[str, Any],
    section_id: str = "",
) -> str:
    """Deterministic comparison blurb when Gemini omits ``narrative_vi`` on a tile."""
    views = int(tile.get("views") or 0)
    handle = str(tile.get("author_handle") or "").strip()
    if handle and not handle.startswith("@"):
        handle = f"@{handle}"

    hook_raw = str(tile.get("hook_type") or "").strip()
    fmt_raw = str(tile.get("content_format") or "").strip()

    # Translate hook and format
    from getviews_pipeline.enum_labels_vi import hook_type_vi

    hook_translated = ""
    if hook_raw:
        hook_translated = hook_type_vi(hook_raw, default="")
        if hook_translated and hook_translated.lower() != "khác":
            hook_translated = f"dạng hook '{hook_translated}'"

    fmt_translated = ""
    if fmt_raw:
        fmt_translated = CONTENT_FORMAT_VI.get(fmt_raw.lower().replace(" ", "_"), "")
        if fmt_translated and fmt_translated.lower() != "khác":
            fmt_translated = f"định dạng '{fmt_translated}'"

    # Views label
    views_label = f"{_format_views_compact_vi(views)} view" if views > 0 else ""

    # Subject
    if handle:
        if views_label:
            subject = f"Kênh {handle} ({views_label})"
        else:
            subject = f"Kênh {handle}"
    else:
        if views_label:
            subject = f"Một video cùng ngách đạt {views_label}"
        else:
            subject = "Một video cùng ngách"

    # Action / context
    details = []
    if fmt_translated:
        details.append(fmt_translated)
    if hook_translated:
        details.append(hook_translated)

    if details:
        action = f"triển khai rất thành công {' kết hợp với '.join(details)}"
    else:
        action = "đang vận hành cực kỳ hiệu quả"

    # Section-specific instruction/value
    angle = _SECTION_TILE_NARRATIVE_ANGLE.get(section_id.strip(), "")
    if not angle:
        angle = "Hãy đối chiếu cách mở đầu và giữ chân của video này để cải thiện cho clip của bạn."

    return f"{subject} {action}. {angle}"


def ensure_distinct_tile_narratives(
    tiles: list[dict[str, Any]],
    section_id: str = "",
) -> None:
    """Regenerate fallback copy when Gemini repeats the same ``narrative_vi`` on multiple tiles."""
    seen: set[str] = set()
    for tile in tiles:
        if not isinstance(tile, dict):
            continue
        narrative = str(tile.get("narrative_vi") or "").strip()
        if not narrative or narrative in seen:
            tile["narrative_vi"] = fallback_tile_narrative_vi(tile, section_id)
        seen.add(str(tile.get("narrative_vi") or "").strip())


def resolve_embedded_tiles(
    tiles: list[dict[str, Any]],
    reference_videos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map aweme_id hints to full reference rows for SectionRenderer."""
    by_id = {
        str(r.get("aweme_id") or r.get("video_id")): r
        for r in reference_videos
        if r.get("aweme_id") or r.get("video_id")
    }
    out: list[dict[str, Any]] = []
    for t in tiles:
        aid = str(t.get("aweme_id") or "")
        src = by_id.get(aid) or {}
        narrative = str(t.get("narrative_vi") or t.get("narrative") or "").strip()
        out.append(
            {
                "aweme_id": aid,
                "thumbnail_url": src.get("thumbnail_url") or t.get("thumbnail_url"),
                "views": int(src.get("views") or 0),
                "caption_snippet": (str(src.get("caption") or src.get("desc") or ""))[
                    :200
                ],
                "video_url": src.get("tiktok_url") or src.get("video_url"),
                "content_format": src.get("content_format"),
                "author_handle": src.get("author_handle"),
                "narrative_vi": narrative or None,
            }
        )
    return out


def approximate_word_count_vi(text: str) -> int:
    """Rough token count — whitespace split + light punctuation strip."""
    if not text.strip():
        return 0
    return len(re.findall(r"[\wÀ-ỹ]+", text, re.UNICODE))
