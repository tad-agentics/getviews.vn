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
    "hook_analysis": "Góc hook: 3 giây đầu mở bằng gì, nhịp cắt và lời thoại khác clip của bạn thế nào.",
    "diagnosis": "Góc hiệu quả: format và cách giữ chân giúp video này chạy tốt trong ngách — áp dụng phần nào cho clip của bạn.",
    "niche_pattern": "Góc pattern: format/hook đang thắng trong ngách — xem họ lặp lại yếu tố nào.",
    "distribution": "Góc phân phối: thời điểm đăng và tín hiệu FYP — so với khung giờ bạn đang dùng.",
    "script_structure": "Góc cấu trúc: nhịp segment và CTA — đối chiếu với timeline clip của bạn.",
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
    desc = str(tile.get("caption_snippet") or "").strip()
    if len(desc) > 100:
        desc = desc[:97] + "…"
    hook = str(tile.get("hook_type") or "").strip()
    fmt = str(tile.get("content_format") or "").strip()
    lead = f"Video tham chiếu «{desc}»" if desc else "Video tham chiếu trong cùng ngách"
    parts = [lead]
    if views > 0:
        parts.append(f"đạt {_format_views_compact_vi(views)} view")
    if handle:
        parts.append(f"từ {handle}")
    if hook:
        parts.append(f"hook {hook}")
    elif fmt:
        parts.append(f"format {fmt}")
    angle = _SECTION_TILE_NARRATIVE_ANGLE.get(section_id.strip(), "")
    body = " — ".join(parts) + "."
    return f"{body} {angle}" if angle else f"{body} So sánh hook và nhịp dẫn với clip của bạn."


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
