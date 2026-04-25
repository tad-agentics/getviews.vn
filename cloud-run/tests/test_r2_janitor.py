"""Tests for ``r2_janitor.run_r2_janitor``.

Pins the contractual behaviours of the R2 storage janitor:
  1. Reads the live ``video_corpus.video_id`` set into memory.
  2. Lists R2 objects under each known prefix (videos/, thumbnails/,
     frames/, video_shots/) and reconciles each key.
  3. Deletes only orphans (key→video_id not in live set).
  4. Skips malformed keys (don't trash unrecognized patterns).
  5. dry_run=True scans + counts but never calls delete_objects.
  6. Exits early when R2 is unconfigured.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from getviews_pipeline.r2_janitor import _extract_video_id, run_r2_janitor


# ── pure functions ───────────────────────────────────────────────────


def test_extract_video_id_recognises_videos_prefix() -> None:
    assert _extract_video_id("videos/", "videos/abc123.mp4") == "abc123"


def test_extract_video_id_recognises_thumbnails_with_any_ext() -> None:
    assert _extract_video_id("thumbnails/", "thumbnails/abc123.jpg") == "abc123"
    assert _extract_video_id("thumbnails/", "thumbnails/abc123.png") == "abc123"
    assert _extract_video_id("thumbnails/", "thumbnails/abc123.webp") == "abc123"


def test_extract_video_id_recognises_frames_indexed_path() -> None:
    assert _extract_video_id("frames/", "frames/abc123/0.png") == "abc123"
    assert _extract_video_id("frames/", "frames/abc123/9.png") == "abc123"


def test_extract_video_id_recognises_video_shots_indexed_path() -> None:
    assert _extract_video_id("video_shots/", "video_shots/abc123/0.jpg") == "abc123"
    assert _extract_video_id("video_shots/", "video_shots/abc123/12.jpg") == "abc123"


def test_extract_video_id_rejects_malformed_keys() -> None:
    """Anything that doesn't match the prefix's pattern returns None —
    operator-visible signal that r2.py and r2_janitor.py drifted."""
    assert _extract_video_id("videos/", "videos/abc123.txt") is None
    assert _extract_video_id("thumbnails/", "thumbnails/abc123") is None
    assert _extract_video_id("frames/", "frames/abc123/0.jpg") is None
    assert _extract_video_id("video_shots/", "video_shots/abc.jpg") is None
    assert _extract_video_id("unknown/", "unknown/abc.jpg") is None


# ── full janitor run with mocked S3 + Supabase ───────────────────────


def _build_supabase_client(video_ids: list[str]) -> MagicMock:
    """Return a Supabase client whose video_corpus paginated SELECT
    yields the given ids on the first page, then []."""
    client = MagicMock()
    rows = [{"video_id": v} for v in video_ids]
    chain = client.table.return_value.select.return_value.order.return_value.limit.return_value
    chain.execute.return_value = MagicMock(data=rows)
    chain.gt.return_value.execute.return_value = MagicMock(data=[])
    return client


def _build_s3_paginator(prefix_to_keys: dict[str, list[str]]) -> MagicMock:
    """Mock S3 list_objects_v2 paginator: per-prefix, yield one page
    containing all keys for that prefix."""
    s3 = MagicMock()

    def get_paginator(_op: str) -> MagicMock:
        paginator = MagicMock()

        def paginate(*, Bucket: str, Prefix: str, MaxKeys: int) -> Any:
            keys = prefix_to_keys.get(Prefix, [])
            return iter([{"Contents": [{"Key": k} for k in keys]}])

        paginator.paginate.side_effect = paginate
        return paginator

    s3.get_paginator.side_effect = get_paginator
    s3.delete_objects.return_value = {"Deleted": [], "Errors": []}
    return s3


def test_dry_run_counts_orphans_without_deleting() -> None:
    """Dry run touches no S3 deletes and reports the orphan/kept split."""
    live = ["live1", "live2"]
    keys_by_prefix = {
        "videos/":      ["videos/live1.mp4", "videos/orphan1.mp4"],
        "thumbnails/":  ["thumbnails/live2.jpg", "thumbnails/orphan2.jpg"],
        "frames/":      ["frames/live1/0.png"],
        "video_shots/": ["video_shots/orphan3/0.jpg",
                         "video_shots/orphan3/1.jpg"],
    }
    client = _build_supabase_client(live)
    s3 = _build_s3_paginator(keys_by_prefix)

    with patch("getviews_pipeline.r2_janitor._get_r2_client", return_value=s3), \
         patch("getviews_pipeline.r2_janitor.r2_configured", return_value=True):
        result = run_r2_janitor(dry_run=True, client=client)

    assert result["mode"] == "dry_run"
    assert result["live_video_ids"] == 2
    # Per-prefix expectations: live1's video kept, orphan1's video orphaned, etc.
    assert result["per_prefix"]["videos/"]["scanned"] == 2
    assert result["per_prefix"]["videos/"]["kept"] == 1
    assert result["per_prefix"]["videos/"]["orphaned"] == 1
    assert result["per_prefix"]["video_shots/"]["orphaned"] == 2
    assert result["total_deleted"] == 0
    s3.delete_objects.assert_not_called()


def test_destructive_run_calls_delete_objects_for_orphans() -> None:
    live = ["live1"]
    keys_by_prefix = {
        "videos/":      ["videos/live1.mp4", "videos/orphan1.mp4"],
        "thumbnails/":  [],
        "frames/":      ["frames/orphan2/0.png"],
        "video_shots/": [],
    }
    client = _build_supabase_client(live)
    s3 = _build_s3_paginator(keys_by_prefix)
    # Simulate R2 confirming both deletes succeeded.
    s3.delete_objects.return_value = {
        "Deleted": [{"Key": "videos/orphan1.mp4"}, {"Key": "frames/orphan2/0.png"}],
        "Errors": [],
    }

    with patch("getviews_pipeline.r2_janitor._get_r2_client", return_value=s3), \
         patch("getviews_pipeline.r2_janitor.r2_configured", return_value=True):
        result = run_r2_janitor(dry_run=False, client=client)

    assert result["mode"] == "destructive"
    # delete_objects called once per non-empty prefix that had orphans.
    assert s3.delete_objects.call_count == 2
    # Total reflects the Deleted rows R2 reported back.
    assert result["total_deleted"] == 4  # mock returns Deleted=2 each call


def test_malformed_keys_are_logged_and_skipped() -> None:
    """A key that doesn't match its prefix's pattern is counted under
    ``malformed`` and never marked orphan — guards against accidental
    cleanup after a key-pattern drift."""
    live = ["live1"]
    keys_by_prefix = {
        "videos/":      ["videos/live1.mp4", "videos/notavideo.txt"],
        "thumbnails/":  [],
        "frames/":      [],
        "video_shots/": [],
    }
    client = _build_supabase_client(live)
    s3 = _build_s3_paginator(keys_by_prefix)

    with patch("getviews_pipeline.r2_janitor._get_r2_client", return_value=s3), \
         patch("getviews_pipeline.r2_janitor.r2_configured", return_value=True):
        result = run_r2_janitor(dry_run=False, client=client)

    assert result["per_prefix"]["videos/"]["malformed"] == 1
    assert result["per_prefix"]["videos/"]["orphaned"] == 0
    s3.delete_objects.assert_not_called()


def test_exits_early_when_r2_unconfigured() -> None:
    """In an environment where R2 envs aren't set the janitor must
    no-op rather than throw — we don't want the cron failing on a
    dev environment."""
    with patch("getviews_pipeline.r2_janitor.r2_configured", return_value=False):
        result = run_r2_janitor(dry_run=False)
    assert result["r2_configured"] is False
    assert result["live_video_ids"] == 0
    assert result["total_deleted"] == 0
    assert result["per_prefix"] == {}
