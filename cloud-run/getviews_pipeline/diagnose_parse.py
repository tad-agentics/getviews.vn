from __future__ import annotations

import re
from typing import Any

from getviews_pipeline.analysis_addressing import AddressingMode

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


_SECTION_TILE_NARRATIVE_ANGLE: dict[str, list[str]] = {
    "hook_analysis": [
        "Hãy quan sát kỹ cách video này tối ưu 3 giây đầu (về nhịp cắt cảnh, cách hiện chữ overlay và hình ảnh mở đầu) để học hỏi cách lôi cuốn người lướt ngay lập tức.",
        "Đặc biệt chú ý đến cú hook mở màn trong 3 giây đầu — cách họ dùng âm thanh kết hợp hình ảnh trực quan để giữ chân người xem không lướt qua.",
        "Hãy tham khảo nhịp điệu mở đầu của clip này, từ cách đặt tiêu đề chữ nổi bật đến việc đổi góc quay nhanh để tạo cảm giác tò mò lập tức."
    ],
    "diagnosis": [
        "Phân tích cách video này xây dựng format và giữ chân khán giả ổn định xuyên suốt thời lượng để áp dụng các điểm tương đồng vào clip của bạn.",
        "Hãy quan sát cấu trúc kịch bản và cách họ sắp xếp diễn biến để giữ nhịp độ cuốn hút từ đầu đến cuối mà không bị nhàm chán.",
        "Chú ý cách họ duy trì tương tác giữa chừng và chốt hạ clip bằng lời kêu gọi hành động tự nhiên, giúp kéo dài thời gian xem trung bình."
    ],
    "niche_pattern": [
        "Đây là một công thức đang thắng lớn trong ngách. Hãy xem cách họ lặp lại các yếu tố cốt lõi để đưa vào kịch bản tiếp theo của bạn.",
        "Một mô-típ nội dung điển hình đang lên xu hướng mạnh mẽ. Bạn có thể học hỏi cách họ khai thác chủ đề quen thuộc nhưng với cách kể mới lạ.",
        "Ý tưởng và phong cách thể hiện này rất được ưa chuộng gần đây. Hãy ứng dụng bộ khung này và lồng ghép cá tính riêng của bạn."
    ],
    "distribution": [
        "Tham khảo khung giờ đăng và nhịp cắn xu hướng của video này để tối ưu hóa thời điểm phân phối hiệu quả nhất cho kênh của bạn.",
        "Quan sát tốc độ tăng trưởng và phản hồi của người xem dưới phần bình luận để rút ra bài học về cách tương tác phù hợp.",
        "Xem xét nhịp đăng tải và cách điều phối nội dung của kênh này nhằm cải thiện chiến lược phân phối video lên xu hướng tốt hơn."
    ],
    "script_structure": [
        "Hãy đối chiếu nhịp phân đoạn, diễn tiến câu chuyện và cách họ chuyển cảnh (transitions) với cấu trúc clip của bạn.",
        "Tham khảo mạch kịch bản chi tiết, sự phân bổ thời lượng giữa các phần và cách chuyển ý mượt mà để hoàn thiện cấu trúc clip của bạn.",
        "Học hỏi nhịp dựng phim, cách ghép nhạc nền bổ trợ cho câu chuyện và lối dẫn dắt gãy gọn để áp dụng vào kịch bản mới."
    ],
}

_SECTION_TILE_NARRATIVE_ANGLE_THIRD: dict[str, list[str]] = {
    "hook_analysis": [
        "So 3 giây đầu (cắt, chữ, hình mở) với clip đang phân tích.",
        "Chú ý hook mở màn — âm + hình giữ người lướt.",
        "Tham khảo nhịp mở: chữ nổi + đổi góc nhanh tạo tò mò.",
    ],
    "diagnosis": [
        "So format và giữ chân suốt clip với video đang phân tích.",
        "Quan sát cấu trúc kịch bản và nhịp cuốn.",
        "Chú ý tương tác giữa clip và CTA chốt.",
    ],
    "niche_pattern": [
        "Công thức đang thắng — creator có thể lặp yếu tố cốt lõi.",
        "Mô-típ đang lên — khai thác chủ đề quen bằng cách kể mới.",
        "Khung được ưa chuộng — lồng cá tính riêng của creator.",
    ],
    "distribution": [
        "Tham khảo giờ đăng và nhịp cắt của video này.",
        "Quan sát bình luận để rút bài học tương tác.",
        "Xem nhịp đăng của kênh tham chiếu.",
    ],
    "script_structure": [
        "So nhịp phân đoạn và chuyển cảnh với clip đang phân tích.",
        "Tham khảo mạch kịch bản và phân bổ thời lượng.",
        "Học nhịp dựng và nhạc nền cho lần quay tiếp theo.",
    ],
}


def _tile_narrative_angles(
    section_id: str,
    addressing_mode: AddressingMode = "third_party",
) -> list[str] | None:
    if addressing_mode == "viewer_own":
        return _SECTION_TILE_NARRATIVE_ANGLE.get(section_id.strip())
    return _SECTION_TILE_NARRATIVE_ANGLE_THIRD.get(section_id.strip())

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


def _tile_hook_fmt_phrases(tile: dict[str, Any]) -> tuple[str, str]:
    """Return (hook_phrase, format_phrase) for narrative — empty if unknown."""
    from getviews_pipeline.enum_labels_vi import hook_type_vi

    hook_raw = str(tile.get("hook_type") or "").strip()
    fmt_raw = str(tile.get("content_format") or "").strip()

    hook_phrase = ""
    if hook_raw:
        hook_vi = hook_type_vi(hook_raw, default="")
        if hook_vi and hook_vi.lower() != "khác":
            hook_phrase = f"hook dạng {hook_vi}"

    fmt_phrase = ""
    if fmt_raw:
        fmt_vi = CONTENT_FORMAT_VI.get(fmt_raw.lower().replace(" ", "_"), "")
        if fmt_vi and fmt_vi.lower() != "khác":
            fmt_phrase = f"format {fmt_vi}"

    return hook_phrase, fmt_phrase


_LEGACY_TILE_NARRATIVE_LEAD_RE = re.compile(
    r"^(?:Kênh|Tài khoản|Nhà sáng tạo|Trang)\s+@\S+",
    re.IGNORECASE,
)


def tile_narrative_needs_regen(narrative: str) -> bool:
    """True when copy repeats handle/views the card footer already shows."""
    n = narrative.strip()
    if not n:
        return True
    if _LEGACY_TILE_NARRATIVE_LEAD_RE.match(n):
        return True
    if re.search(r"@\w", n) and re.search(r"[\d.,]+[KM]?\s*view", n, re.IGNORECASE):
        return True
    return False


def _reference_strength_sentence(
    tile: dict[str, Any],
    idx: int,
    addressing_mode: AddressingMode = "third_party",
) -> str:
    """Why this peer was picked — no @handle or view count (shown on card footer)."""
    hook_phrase, fmt_phrase = _tile_hook_fmt_phrases(tile)
    if hook_phrase and fmt_phrase:
        templates = [
            f"Được chọn vì {hook_phrase} trên nền {fmt_phrase} giữ chân rõ ngay từ nhịp mở.",
            f"Tham chiếu vì {fmt_phrase} kết hợp {hook_phrase} tạo lý do dừng lướt ngay đầu clip.",
            f"Lý do tham chiếu: {hook_phrase} và {fmt_phrase} làm tốt hơn median ngách ở cùng góc so sánh.",
        ]
    elif hook_phrase:
        if addressing_mode == "viewer_own":
            templates = [
                f"Được chọn vì {hook_phrase} tạo lý do dừng lướt ngay 3 giây đầu.",
                f"Tham chiếu vì {hook_phrase} mạnh hơn cách mở clip của bạn ở cùng chủ đề.",
                f"Lý do tham chiếu: {hook_phrase} giữ nhịp tò mò ngay khung mở.",
            ]
        else:
            templates = [
                f"Được chọn vì {hook_phrase} tạo lý do dừng lướt ngay 3 giây đầu.",
                f"Tham chiếu vì {hook_phrase} mạnh hơn cách mở clip đang phân tích ở cùng chủ đề.",
                f"Lý do tham chiếu: {hook_phrase} giữ nhịp tò mò ngay khung mở.",
            ]
    elif fmt_phrase:
        if addressing_mode == "viewer_own":
            templates = [
                f"Được chọn vì {fmt_phrase} giữ nhịp và cấu trúc ổn định suốt clip.",
                f"Tham chiếu vì {fmt_phrase} duy trì momentum giữa clip tốt hơn median.",
                f"Lý do tham chiếu: {fmt_phrase} là điểm mạnh cần đối chiếu với video của bạn.",
            ]
        else:
            templates = [
                f"Được chọn vì {fmt_phrase} giữ nhịp và cấu trúc ổn định suốt clip.",
                f"Tham chiếu vì {fmt_phrase} duy trì momentum giữa clip tốt hơn median.",
                f"Lý do tham chiếu: {fmt_phrase} là điểm mạnh cần đối chiếu với video này.",
            ]
    else:
        templates = [
            "Được chọn vì cấu trúc format và nhịp dẫn nhất quán suốt clip.",
            "Tham chiếu vì clip này giữ chân ổn định hơn median ở cùng ngách.",
            "Lý do tham chiếu: nhịp dựng và cách triển khai ý chính rõ ràng, dễ học theo.",
        ]
    return templates[idx % len(templates)]


def fallback_tile_narrative_vi(
    tile: dict[str, Any],
    section_id: str = "",
    idx: int = 0,
    addressing_mode: AddressingMode = "third_party",
) -> str:
    """Deterministic comparison blurb when Gemini omits ``narrative_vi`` on a tile."""
    strength = _reference_strength_sentence(tile, idx, addressing_mode)

    angles = _tile_narrative_angles(section_id, addressing_mode)
    if angles:
        angle = angles[idx % len(angles)]
    elif addressing_mode == "viewer_own":
        if idx % 3 == 0:
            angle = "Đối chiếu cách mở đầu và giữ chân với clip của bạn."
        elif idx % 3 == 1:
            angle = "Quan sát nhịp truyền tải và cách chốt ý để áp dụng cho video tiếp theo."
        else:
            angle = "Học cách họ duy trì momentum giữa clip mà không bị rời nhịp."
    else:
        if idx % 3 == 0:
            angle = "Đối chiếu cách mở đầu và giữ chân với clip đang phân tích."
        elif idx % 3 == 1:
            angle = "Quan sát nhịp truyền tải và cách chốt ý cho lần quay tiếp theo của creator."
        else:
            angle = "Học cách duy trì momentum giữa clip mà không bị rời nhịp."

    return f"{strength} {angle}"


def ensure_distinct_tile_narratives(
    tiles: list[dict[str, Any]],
    section_id: str = "",
    addressing_mode: AddressingMode = "third_party",
) -> None:
    """Regenerate fallback copy when Gemini repeats the same ``narrative_vi`` on multiple tiles."""
    seen: set[str] = set()
    for idx, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            continue
        narrative = str(tile.get("narrative_vi") or "").strip()
        if not narrative or narrative in seen or tile_narrative_needs_regen(narrative):
            tile["narrative_vi"] = fallback_tile_narrative_vi(
                tile, section_id, idx, addressing_mode
            )
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
