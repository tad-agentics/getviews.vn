"""Launch Phase 1 — channel quick peek F5 full payload."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from getviews_pipeline.channel_quick_peek import channel_quick_peek_for_handle


def _corpus_rows(*, high_entropy: bool = False) -> list[dict]:
    rows = []
    fmts = (
        ["fmt_a", "fmt_b", "fmt_c", "fmt_d", "fmt_e", "fmt_f"]
        if high_entropy
        else ["talking_head", "montage"]
    )
    for i, views in enumerate([120, 280, 450, 900, 1200, 300]):
        rows.append(
            {
                "video_id": f"vid{i}",
                "views": views,
                "likes": views // 20,
                "comments": 3,
                "content_format": fmts[i % len(fmts)],
                "posted_at": f"2026-05-{10 + i:02d}T12:00:00+00:00",
                "hook_type": "bold_claim" if i < 4 else "question",
                "breakout_multiplier": 2.5 if i == 4 else 1.0,
                "content_class_id": 42,
                "ingest_loop_niche_id": 3,
                "creator_tier": "micro",
            }
        )
    return rows


@patch("getviews_pipeline.channel_quick_peek.get_service_client")
def test_channel_quick_peek_full_f5_payload(mock_client: MagicMock) -> None:
    sb = MagicMock()
    mock_client.return_value = sb
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=_corpus_rows()
    )

    payload = channel_quick_peek_for_handle("@creator")

    assert payload["corpus_video_count"] == 6
    assert payload["median_views"] == 375
    assert payload["dominant_hook"] in {"bold_claim", "question"}
    assert payload["breakout_video"] is not None
    assert payload["breakout_video"]["video_id"] == "vid4"
    assert isinstance(payload["findings"], list)
    assert payload["channel_summary"] is not None
    assert payload["channel_summary"]["avg_views"] > 0
    assert payload["channel_summary"]["posts_per_week"] > 0


@patch("getviews_pipeline.channel_quick_peek.fetch_niche_benchmarks", return_value={})
@patch("getviews_pipeline.channel_quick_peek.get_service_client")
def test_channel_quick_peek_surfaces_format_entropy_teaser(
    mock_client: MagicMock,
    _mock_benchmarks: MagicMock,
) -> None:
    sb = MagicMock()
    mock_client.return_value = sb
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=_corpus_rows(high_entropy=True)
    )
    sb.table.return_value.select.return_value.neq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {"content_format": "peer_fmt", "views": 9000, "creator_handle": "peer1"},
            {"content_format": "peer_fmt", "views": 8000, "creator_handle": "peer2"},
        ]
    )

    payload = channel_quick_peek_for_handle("@creator")

    finding_ids = [row["finding_id"] for row in payload["findings"]]
    assert "channel_format_entropy_high" in finding_ids
    entropy_row = next(
        row for row in payload["findings"] if row["finding_id"] == "channel_format_entropy_high"
    )
    assert "entropy=" in entropy_row["teaser"]
