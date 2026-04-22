"""Tests for ``content_format_reclassify.run_content_format_reclassify``.

Pins three contractual behaviours:
  1. Scans both ``content_format='other'`` AND ``content_format IS NULL``.
  2. Only UPDATEs rows whose re-classification actually changes.
  3. Paginates until exhausted (multi-page scan).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from getviews_pipeline.content_format_reclassify import (
    run_content_format_reclassify,
)


def _build_client(pages: list[list[dict[str, Any]]]) -> MagicMock:
    """Mock a paginated SELECT: each call to .execute() returns the next
    page. Updates succeed with empty data."""
    client = MagicMock()

    select_chain = MagicMock()
    # We bypass the real query filters because our test only cares about
    # how results are consumed, not how the .or_/.order/.limit chain is
    # built. Every page request returns the next page in sequence.
    limit_call = (
        select_chain.or_.return_value
        .order.return_value
        .limit.return_value
    )
    gt_call = limit_call.gt.return_value
    limit_call.execute.side_effect = [MagicMock(data=p) for p in pages]
    gt_call.execute.side_effect = [MagicMock(data=p) for p in pages[1:]]

    client.table.return_value.select.return_value = select_chain
    update_chain = client.table.return_value.update.return_value.eq.return_value.execute
    update_chain.return_value = MagicMock(data=[])
    return client


def test_reclassify_updates_only_rows_whose_bucket_changes() -> None:
    """Row with a tax transcript should move 'other' → 'tutorial'; a
    row with pure entertainment transcript stays 'other' and is not
    updated."""
    page = [
        {
            "video_id": "tax-001",
            "niche_id": 15,
            "content_format": "other",
            "created_at": "2026-04-01T00:00:00Z",
            "analysis_json": {
                "audio_transcript": "Khẩn: Kiểm tra quyết toán thuế ngay",
                "topics": ["Thuế"],
                "scenes": [],
                "tone": "",
            },
        },
        {
            "video_id": "misc-002",
            "niche_id": 13,
            "content_format": "other",
            "created_at": "2026-04-01T00:00:01Z",
            "analysis_json": {
                "audio_transcript": "[Music playing]",
                "topics": ["comedy"],
                "scenes": [],
                "tone": "",
            },
        },
    ]
    client = _build_client([page, []])

    result = run_content_format_reclassify(client=client, page_size=500)

    assert result["scanned"] == 2
    assert result["reclassified"] == 1
    assert result["still_other"] == 1
    assert result["by_bucket"] == {"tutorial": 1}

    # Only one UPDATE fired — for the tax row.
    assert client.table.return_value.update.call_count == 1
    update_payload = client.table.return_value.update.call_args.args[0]
    assert update_payload == {"content_format": "tutorial"}
    eq_call = client.table.return_value.update.return_value.eq.call_args
    assert eq_call.args == ("video_id", "tax-001")


def test_reclassify_handles_null_content_format() -> None:
    """Rows with content_format=NULL are scanned + updated if classifier
    returns something. (The .or_ filter in the real query selects both
    'other' and NULL.)"""
    page = [
        {
            "video_id": "null-001",
            "niche_id": 16,
            "content_format": None,
            "created_at": "2026-04-01T00:00:00Z",
            "analysis_json": {
                "audio_transcript": "Nàng dâu Philippines lấy chồng Hàn Quốc",
                "topics": [],
                "scenes": [],
                "tone": "",
            },
        },
    ]
    client = _build_client([page, []])

    result = run_content_format_reclassify(client=client, page_size=500)

    assert result["reclassified"] == 1
    assert result["by_bucket"] == {"storytelling": 1}


def test_reclassify_paginates_until_exhausted() -> None:
    """Two full pages + one partial should terminate at the partial page."""
    def _row(i: int, transcript: str) -> dict[str, Any]:
        return {
            "video_id": f"v{i}",
            "niche_id": 13,
            "content_format": "other",
            "created_at": f"2026-04-01T00:00:{i:02d}Z",
            "analysis_json": {
                "audio_transcript": transcript,
                "topics": [],
                "scenes": [],
                "tone": "",
            },
        }

    page_size = 3
    pages = [
        [_row(1, "câu chuyện kể về"), _row(2, "không gì"), _row(3, "bí quyết làm việc")],
        [_row(4, "màn trình diễn quá hay")],
        [],
    ]
    client = _build_client(pages)

    result = run_content_format_reclassify(client=client, page_size=page_size)

    # 4 rows total scanned across both pages (last empty page terminates)
    assert result["scanned"] == 4
    # v1 → storytelling, v3 → tutorial, v4 → review. v2 stays 'other'.
    assert result["reclassified"] == 3
    assert result["still_other"] == 1
    assert sum(result["by_bucket"].values()) == 3


def test_reclassify_update_failure_counts_as_error() -> None:
    """A single row's UPDATE failing must not abort the scan."""
    page = [
        {
            "video_id": "tax-001",
            "niche_id": 15,
            "content_format": "other",
            "created_at": "2026-04-01T00:00:00Z",
            "analysis_json": {
                "audio_transcript": "Khẩn: Kiểm tra quyết toán thuế",
                "topics": [], "scenes": [], "tone": "",
            },
        },
    ]
    client = _build_client([page, []])
    update_chain = client.table.return_value.update.return_value.eq.return_value.execute
    update_chain.side_effect = RuntimeError("db down")

    result = run_content_format_reclassify(client=client, page_size=500)

    assert result["errors"] == 1
    assert result["reclassified"] == 0
