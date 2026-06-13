"""Who the diagnosis addresses — viewer's own video vs third-party paste-link."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

AddressingMode = Literal["viewer_own", "third_party"]


def normalize_tiktok_handle(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.strip().lstrip("@").strip().lower()


def resolve_video_addressing_mode(
    *,
    video_creator_handle: str | None,
    viewer_tiktok_handle: str | None,
) -> AddressingMode:
    """``viewer_own`` only when the logged-in profile handle matches the video author."""
    video = normalize_tiktok_handle(video_creator_handle)
    viewer = normalize_tiktok_handle(viewer_tiktok_handle)
    if video and viewer and video == viewer:
        return "viewer_own"
    return "third_party"


def fetch_viewer_tiktok_handle(user_sb: Any | None, user_id: str | None) -> str | None:
    if not user_sb or not user_id:
        return None
    try:
        pres = (
            user_sb.table("profiles")
            .select("tiktok_handle")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.debug("[addressing] profile tiktok_handle read failed: %s", exc)
        return None
    row = pres.data if pres else None
    if not isinstance(row, dict):
        return None
    handle = (row.get("tiktok_handle") or "").strip()
    return handle or None


def creator_ref_label(creator_handle: str | None) -> str:
    norm = normalize_tiktok_handle(creator_handle)
    return f"@{norm}" if norm else "creator"


def build_addressing_prompt_block(
    mode: AddressingMode,
    *,
    creator_handle: str | None = None,
) -> str:
    ref = creator_ref_label(creator_handle)
    if mode == "viewer_own":
        return (
            "ĐỐI TƯỢNG ĐỌC: Video thuộc kênh TikTok đã gắn trên tài khoản — "
            "có thể dùng \"video của bạn\", \"kênh của bạn\", \"bạn cần\" khi tự nhiên. "
            "CHANNEL-FIRST vẫn áp dụng với dữ liệu kênh của chính creator đó."
        )
    return f"""ĐỐI TƯỢNG ĐỌC (BẮT BUỘC — ưu tiên cao hơn mọi ví dụ \"bạn/của bạn\" trong voice guide):
Người dùng Studio chỉ dán link — video thuộc creator {ref}, không chắc là video của người đang đọc.
- Dùng ngôi thứ ba về creator: \"video này\", \"kênh {ref}\", \"creator\", \"clip này\".
- CẤM: \"video của bạn\", \"clip của bạn\", \"kênh của bạn\", \"bạn cần\", \"ngách của bạn\" (→ \"ngách này\").
- CHANNEL-FIRST: so sánh với dữ liệu kênh của {ref}, không \"kênh bạn\".
- embedded_tiles: so với \"clip đang phân tích\" / \"video này\", không \"clip của bạn\".
- fix_vi: hướng dẫn cho creator {ref} — \"creator nên…\", không \"bạn nên\"."""
