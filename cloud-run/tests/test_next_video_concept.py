"""derive_next_video_concept — peer-average zero guard (2026-06-12).

Peers built by the live-enrich fallback can carry ``avg_views=0``; the
deterministic rationale used to render "trung bình ~0" and the FE box showed
"Peer TB ~ 0 view".
"""

from __future__ import annotations

from typing import Any

from getviews_pipeline.channel_diagnose import derive_next_video_concept


def _peer(avg_views: float) -> dict[str, Any]:
    return {
        "handle": "peer1",
        "followers": 10_000,
        "avg_views": avg_views,
        "engagement_rate": 0.0,
        "format_label": "talking_head",
        "sample_videos": [
            {
                "thumbnail_url": "https://cdn.example/t.jpg",
                "views": 90_000,
                "video_url": "https://www.tiktok.com/@peer1/video/1",
            }
        ],
    }


def _videos() -> list[dict[str, Any]]:
    # 1/10 talking_head → share 10% < 45% gap threshold.
    return [
        {"content_format": "talking_head", "duration_sec": 20},
        *[{"content_format": "product_closeup", "duration_sec": 15} for _ in range(9)],
    ]


def test_rationale_includes_peer_average_when_real() -> None:
    concept = derive_next_video_concept([_peer(120_000)], {}, _videos())
    assert concept is not None
    assert concept["peer_avg_views"] == 120_000
    assert "trung bình ~" in concept["rationale_struct"]
    assert "~0" not in concept["rationale_struct"]


def test_rationale_omits_peer_average_when_zero() -> None:
    concept = derive_next_video_concept([_peer(0)], {}, _videos())
    assert concept is not None
    assert concept["peer_avg_views"] == 0
    assert "trung bình" not in concept["rationale_struct"]
    assert "~0" not in concept["rationale_struct"]
    # The format-gap claim must survive without the broken number.
    assert "1/10 video" in concept["rationale_struct"]
