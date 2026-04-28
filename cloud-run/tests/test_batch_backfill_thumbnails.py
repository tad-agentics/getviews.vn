"""``POST /batch/backfill-thumbnails`` — legacy-row self-heal.

Per-row strategy under test:

  1. **R2 frame[0] copy** — server-side ``copy_object`` from
     ``frames/{vid}/0.png``. Zero CDN cost. Chosen when frame exists.
  2. **CDN mirror fallback** — only when frame copy returns ``None`` and
     the row carries a non-empty ``thumbnail_url``.
  3. **NULL the column** — both miss. The FE handles NULL via the new
     ``<VideoThumbnail>`` placeholder; the row stays in the candidate
     set on rerun (so a later re-analysis can heal it).

Rows already on the R2 public URL are skipped. The Supabase read is
paginated (1000-row default would silently truncate the ~46K corpus).

These tests mock the helpers + supabase client to stay hermetic — no
network, no R2 credentials needed.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_SECRET = "test-batch-secret-backfill"
_R2_PUBLIC = "https://r2.test"


@pytest.fixture(scope="module")
def client():  # type: ignore[return]
    try:
        import main as m  # type: ignore[import-not-found]
        with patch.dict(os.environ, {"BATCH_SECRET": _SECRET}):
            yield TestClient(m.app, raise_server_exceptions=False)
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Cannot import main: {exc}")


# ── Fake Supabase client ────────────────────────────────────────────
#
# Just enough surface to cover ``.table(t).select(c).range(a,b).execute()``
# for reads and ``.table(t).update(p).eq(c, v).execute()`` for writes.
# The router uses both; everything else is irrelevant.


class _FakeUpdate:
    def __init__(self, parent: _FakeTable, patch_payload: dict) -> None:
        self._parent = parent
        self._patch = patch_payload

    def eq(self, col: str, val) -> _FakeUpdate:
        self._parent.updates.append({"col": col, "val": val, "patch": self._patch})
        return self

    def execute(self):
        return MagicMock(data=None)


class _FakeSelect:
    def __init__(self, parent: _FakeTable) -> None:
        self._parent = parent

    def range(self, lo: int, hi: int) -> _FakeSelect:
        self._range = (lo, hi)
        return self

    def execute(self):
        lo, hi = self._range
        # Supabase .range is inclusive on both ends.
        return MagicMock(data=self._parent.rows[lo:hi + 1])


class _FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.updates: list[dict] = []

    def select(self, *_a, **_kw) -> _FakeSelect:
        return _FakeSelect(self)

    def update(self, patch_payload: dict) -> _FakeUpdate:
        return _FakeUpdate(self, patch_payload)


class _FakeSb:
    def __init__(self, rows: list[dict]) -> None:
        self.video_corpus = _FakeTable(rows)

    def table(self, name: str) -> _FakeTable:
        assert name == "video_corpus", f"unexpected table {name!r}"
        return self.video_corpus


# ── Helpers ─────────────────────────────────────────────────────────


def _patch_r2_env():
    """Force ``r2_configured()`` true and pin the public URL the router
    uses to identify already-backfilled rows."""
    return patch.multiple(
        "getviews_pipeline.r2",
        R2_ACCOUNT_ID="test-account",
        R2_ACCESS_KEY_ID="test-key",
        R2_SECRET_ACCESS_KEY="test-secret",
        R2_PUBLIC_URL=_R2_PUBLIC,
        R2_BUCKET_NAME="test-bucket",
    )


def _post(client: TestClient):
    return client.post(
        "/batch/backfill-thumbnails",
        headers={"X-Batch-Secret": _SECRET},
        json={},
    )


# ── 1. Frame[0] copy succeeds → R2 URL written, no CDN call ────────


def test_frame_copy_path_skips_cdn_and_writes_r2_url(client: TestClient) -> None:
    """When ``copy_first_frame_to_thumbnail`` returns a URL we must
    write it back and NEVER touch the CDN mirror — the whole point of
    the architecture is one CDN pull per video, ever."""
    rows = [{"video_id": "v1", "thumbnail_url": "https://tiktok.cdn/old.jpg"}]
    fake_sb = _FakeSb(rows)
    cdn_mock = AsyncMock(return_value="should-not-be-called")

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail",
               return_value=f"{_R2_PUBLIC}/thumbnails/v1.png"), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail", cdn_mock), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "ok": True,
        "from_frame": 1,
        "from_cdn": 0,
        "nulled": 0,
        "failed": 0,
        "total": 1,
    }
    cdn_mock.assert_not_awaited()
    assert fake_sb.video_corpus.updates == [
        {"col": "video_id", "val": "v1",
         "patch": {"thumbnail_url": f"{_R2_PUBLIC}/thumbnails/v1.png"}},
    ]


# ── 2. Frame missing, CDN mirror succeeds ──────────────────────────


def test_cdn_fallback_when_frame_missing(client: TestClient) -> None:
    """Frame copy returns None (no analysis frame uploaded yet) → fall
    through to CDN mirror. The mirrored URL gets written."""
    rows = [{"video_id": "v2", "thumbnail_url": "https://tiktok.cdn/x.jpg"}]
    fake_sb = _FakeSb(rows)
    cdn_mock = AsyncMock(return_value=f"{_R2_PUBLIC}/thumbnails/v2.jpg")

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail", return_value=None), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail", cdn_mock), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["from_frame"] == 0
    assert body["from_cdn"] == 1
    assert body["nulled"] == 0
    cdn_mock.assert_awaited_once_with("https://tiktok.cdn/x.jpg", "v2")
    assert fake_sb.video_corpus.updates == [
        {"col": "video_id", "val": "v2",
         "patch": {"thumbnail_url": f"{_R2_PUBLIC}/thumbnails/v2.jpg"}},
    ]


# ── 3. Both miss → NULL written ────────────────────────────────────


def test_nulls_when_frame_and_cdn_both_miss(client: TestClient) -> None:
    """Frame copy returns None AND CDN mirror returns None (URL expired
    + frame never uploaded) → NULL the column so the FE renders the
    placeholder cleanly. Row stays eligible for rerun."""
    rows = [{"video_id": "v3", "thumbnail_url": "https://tiktok.cdn/dead.jpg"}]
    fake_sb = _FakeSb(rows)

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail", return_value=None), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail",
               new=AsyncMock(return_value=None)), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["nulled"] == 1
    assert body["from_frame"] == 0 and body["from_cdn"] == 0 and body["failed"] == 0
    assert fake_sb.video_corpus.updates == [
        {"col": "video_id", "val": "v3", "patch": {"thumbnail_url": None}},
    ]


# ── 4. NULL CDN URL + frame copy succeeds → still healed ───────────


def test_null_cdn_url_still_healed_via_frame_copy(client: TestClient) -> None:
    """Rows with NULL ``thumbnail_url`` must NOT be filtered out — the
    whole point of the upgraded route is that we can self-heal them
    from R2 frame[0] alone, no CDN URL needed."""
    rows = [{"video_id": "v4", "thumbnail_url": None}]
    fake_sb = _FakeSb(rows)
    cdn_mock = AsyncMock(return_value="must-not-be-called")

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail",
               return_value=f"{_R2_PUBLIC}/thumbnails/v4.png"), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail", cdn_mock), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["from_frame"] == 1
    cdn_mock.assert_not_awaited()


# ── 5. NULL CDN URL + frame missing → NULL stays NULL, no CDN call ─


def test_null_cdn_url_with_no_frame_does_not_touch_cdn(client: TestClient) -> None:
    """If the row has NULL ``thumbnail_url`` AND frame[0] doesn't exist,
    the CDN fallback has no URL to fetch — must skip CDN entirely and
    record as nulled."""
    rows = [{"video_id": "v5", "thumbnail_url": None}]
    fake_sb = _FakeSb(rows)
    cdn_mock = AsyncMock(return_value="must-not-be-called")

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail", return_value=None), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail", cdn_mock), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["nulled"] == 1
    assert body["from_cdn"] == 0
    cdn_mock.assert_not_awaited()


# ── 6. Already-on-R2 rows skipped (no copy attempt, no DB write) ───


def test_already_r2_rows_are_skipped(client: TestClient) -> None:
    """Rows whose ``thumbnail_url`` already points at the R2 public
    URL are filtered out before any per-row work — keeps reruns cheap."""
    rows = [
        {"video_id": "vA", "thumbnail_url": f"{_R2_PUBLIC}/thumbnails/vA.png"},
        {"video_id": "vB", "thumbnail_url": f"{_R2_PUBLIC}/thumbnails/vB.jpg"},
    ]
    fake_sb = _FakeSb(rows)
    frame_mock = MagicMock(return_value="must-not-be-called")
    cdn_mock = AsyncMock(return_value="must-not-be-called")

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail", frame_mock), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail", cdn_mock), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["from_frame"] == body["from_cdn"] == body["nulled"] == 0
    frame_mock.assert_not_called()
    cdn_mock.assert_not_awaited()
    assert fake_sb.video_corpus.updates == []


# ── 7. Pagination — read more than 1000 rows ───────────────────────


class _PaginatingTable(_FakeTable):
    """Variant that records every ``range`` call so we can assert the
    router didn't stop at the 1000-row Supabase default."""

    def __init__(self, rows: list[dict]) -> None:
        super().__init__(rows)
        self.range_calls: list[tuple[int, int]] = []

    def select(self, *_a, **_kw) -> _FakeSelect:  # type: ignore[override]
        outer = self

        class _Sel(_FakeSelect):
            def range(self, lo: int, hi: int):
                outer.range_calls.append((lo, hi))
                return super().range(lo, hi)

        return _Sel(self)


class _PaginatingSb:
    def __init__(self, rows: list[dict]) -> None:
        self.video_corpus = _PaginatingTable(rows)

    def table(self, name: str):
        return self.video_corpus


def test_pagination_reads_past_first_1000(client: TestClient) -> None:
    """Corpus is ~46K rows; supabase-py's default execute returns 1000.
    Router must paginate via ``.range()`` until a short batch returns."""
    # 1000 rows already on R2 (skipped), then 5 rows needing backfill —
    # forces at least two range() calls.
    on_r2 = [
        {"video_id": f"r{i}", "thumbnail_url": f"{_R2_PUBLIC}/thumbnails/r{i}.png"}
        for i in range(1000)
    ]
    needs = [{"video_id": f"n{i}", "thumbnail_url": None} for i in range(5)]
    sb = _PaginatingSb(on_r2 + needs)

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail",
               side_effect=lambda vid: f"{_R2_PUBLIC}/thumbnails/{vid}.png"), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail",
               new=AsyncMock(return_value=None)), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert body["from_frame"] == 5
    # Two pages: (0..999), (1000..1999) — second returns 5 rows so loop exits.
    assert sb.video_corpus.range_calls == [(0, 999), (1000, 1999)]


# ── 8. Per-row exceptions don't poison the whole batch ─────────────


def test_per_row_exception_is_isolated(client: TestClient) -> None:
    """If one row's helpers raise, only that row counts as failed —
    the rest of the batch must still process."""
    rows = [
        {"video_id": "ok1", "thumbnail_url": "https://cdn/old.jpg"},
        {"video_id": "boom", "thumbnail_url": "https://cdn/old.jpg"},
        {"video_id": "ok2", "thumbnail_url": "https://cdn/old.jpg"},
    ]
    fake_sb = _FakeSb(rows)

    def _frame_side_effect(vid: str):
        if vid == "boom":
            raise RuntimeError("R2 client exploded")
        return f"{_R2_PUBLIC}/thumbnails/{vid}.png"

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail",
               side_effect=_frame_side_effect), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail",
               new=AsyncMock(return_value=None)), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["from_frame"] == 2
    assert body["failed"] == 1
    # The failing row must NOT have written anything (no NULL, no patch).
    written_ids = [u["val"] for u in fake_sb.video_corpus.updates]
    assert "boom" not in written_ids
    assert set(written_ids) == {"ok1", "ok2"}


# ── 9. R2 not configured → 500 (not silent) ────────────────────────


def test_500_when_r2_not_configured(client: TestClient) -> None:
    """Without R2 credentials we have no permanent storage — the
    backfill is a no-op and the operator needs to know."""
    with patch("getviews_pipeline.r2.r2_configured", return_value=False):
        resp = _post(client)
    assert resp.status_code == 500
    assert "R2" in resp.text


# ── 10. CDN mirror raising is treated as miss, not failure ─────────


def test_cdn_mirror_exception_falls_through_to_null(client: TestClient) -> None:
    """``download_and_upload_thumbnail`` may raise on proxy timeout /
    DNS / etc. The router wraps that in a try/except and treats it as
    a miss (NULL the row) so the whole batch keeps moving."""
    rows = [{"video_id": "vX", "thumbnail_url": "https://cdn/x.jpg"}]
    fake_sb = _FakeSb(rows)

    with _patch_r2_env(), \
         patch("getviews_pipeline.config.R2_PUBLIC_URL", _R2_PUBLIC), \
         patch("getviews_pipeline.r2.copy_first_frame_to_thumbnail", return_value=None), \
         patch("getviews_pipeline.r2.download_and_upload_thumbnail",
               new=AsyncMock(side_effect=RuntimeError("proxy timeout"))), \
         patch("getviews_pipeline.supabase_client.get_service_client",
               return_value=fake_sb):
        resp = _post(client)

    assert resp.status_code == 200
    body = resp.json()
    assert body["nulled"] == 1
    assert body["failed"] == 0
