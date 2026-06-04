"""Session niche must win over hashtag inference in Studio."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from getviews_pipeline.live_niche import resolve_live_niche_id


def test_session_niche_before_hashtag_classify() -> None:
    aweme = {
        "desc": "#iphone #tech review",
        "author": {"unique_id": "techcreator"},
        "text_extra": [{"hashtag_name": "iphone"}],
    }
    with patch(
        "getviews_pipeline.creator_blocklist.niche_override_for_handle",
        return_value=None,
    ), patch(
        "getviews_pipeline.hashtag_niche_map.classify_from_hashtags",
        new_callable=AsyncMock,
        return_value=9,
    ) as classify_mock:
        nid = asyncio.run(
            resolve_live_niche_id(
                MagicMock(),
                aweme,
                fallback_session_niche_id=27,
                user_id=None,
            )
        )
    assert nid == 27
    classify_mock.assert_not_called()
