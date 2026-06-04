"""On-demand niche resolution ladder (distinct from batch ingest loop niche)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def caption_for_niche_resolution(aweme: dict[str, Any], description: str = "") -> str:
    """``desc`` + challenge titles — aligned with corpus ingest."""
    desc_raw = str(aweme.get("desc") or description or "")
    challenge_titles = [
        str(c.get("title") or "")
        for c in (aweme.get("challenges") or [])
        if c.get("title")
    ]
    return f"{desc_raw} {' '.join(challenge_titles)}".strip()


async def resolve_live_niche_id(
    service_sb: Any,
    aweme: dict[str, Any],
    *,
    fallback_session_niche_id: int | None = None,
    user_id: str | None = None,
) -> int:
    """CREATOR_NICHE_OVERRIDE → session (when set) → hashtags → caption → profile."""
    from getviews_pipeline import ensemble
    from getviews_pipeline.creator_blocklist import niche_override_for_handle
    from getviews_pipeline.hashtag_niche_map import classify_from_hashtags
    from getviews_pipeline.niche_match import find_niche_match
    from getviews_pipeline.profile_niches import resolve_legacy_niche_from_profile_row

    meta = ensemble.parse_metadata(aweme)
    handle = ""
    if meta.author and meta.author.username:
        handle = meta.author.username
    if not handle:
        author = aweme.get("author") if isinstance(aweme.get("author"), dict) else {}
        handle = str(author.get("unique_id") or "")

    override = niche_override_for_handle(handle)
    if override is not None:
        return int(override)

    # Studio answer sessions pin cohort to the user's selected niche — do not
    # let video hashtags / caption classifier override session or profile.
    if fallback_session_niche_id and int(fallback_session_niche_id) > 0:
        return int(fallback_session_niche_id)

    try:
        nid = await classify_from_hashtags(meta.hashtags, service_sb)
        if nid:
            return int(nid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[live_niche] hashtag classify failed: %s", exc)

    caption = caption_for_niche_resolution(aweme, meta.description or "")
    if caption:
        try:
            match = find_niche_match(service_sb, caption)
            if match is not None:
                return int(match.niche_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[live_niche] caption niche match failed: %s", exc)

    if user_id:
        try:
            row = (
                service_sb.table("profiles")
                .select("creator_niche_id")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            profile = row.data if row is not None else None
            legacy = resolve_legacy_niche_from_profile_row(profile)
            if legacy:
                return int(legacy)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[live_niche] profile creator_niche lookup failed: %s", exc)

    return 0


__all__ = ["caption_for_niche_resolution", "resolve_live_niche_id"]
