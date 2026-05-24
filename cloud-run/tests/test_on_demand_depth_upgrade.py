"""S4-1 — on-demand basic→deep synthesis-only upgrade (§4.12.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from getviews_pipeline.video_analyze import (
    EXTRACT_JSON_SCHEMA_VERSION,
    ON_DEMAND_RESPONSE_SCHEMA_VERSION,
    _persist_on_demand_cache,
    _strip_on_demand_client_cache_fields,
    _try_on_demand_basic_upgrade_source,
    _try_on_demand_cache_hit,
    run_video_analyze_on_demand,
)

URL = "https://www.tiktok.com/@creator/video/7630766288574369045"
VID = "7630766288574369045"
EXTRACT = {"hook_analysis": {"hook_type": "demo", "hook_phrase": "x"}}


def _fresh_basic_cached(*, with_extract: bool = True) -> dict:
    cached: dict = {
        "video_id": VID,
        "source": "on_demand",
        "mode": "win",
        "meta": {"views": 50_000, "content_format": "talking_head", "caption": "cap"},
        "narrative_vi": {"van_de_chinh": "basic only"},
        "analysis_depth": "basic",
        "response_schema_version": ON_DEMAND_RESPONSE_SCHEMA_VERSION,
    }
    if with_extract:
        cached["extract_json"] = EXTRACT
        cached["extract_schema_version"] = EXTRACT_JSON_SCHEMA_VERSION
    return cached


def _service_sb_with_basic_row(cached: dict) -> MagicMock:
    row = {
        "cached_response": cached,
        "computed_at": datetime.now(UTC).isoformat(),
    }

    class _Exec:
        data = [row]

    class _Query:
        def select(self, *_: object, **__: object) -> _Query:
            return self

        def eq(self, *_: object, **__: object) -> _Query:
            return self

        def limit(self, *_: object, **__: object) -> _Query:
            return self

        def execute(self) -> _Exec:
            return _Exec()

    sb = MagicMock()
    sb.table.return_value = _Query()
    return sb


def test_basic_with_extract_json_upgrade_skips_fetch():
    sb = _service_sb_with_basic_row(_fresh_basic_cached())
    with patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
    ) as fetch_mock:
        out = _try_on_demand_basic_upgrade_source(sb, URL)
    fetch_mock.assert_not_called()
    assert out is not None
    assert out["__narrative_analysis"] == EXTRACT
    assert out["__analysis_depth"] == "deep"
    assert "narrative_vi" not in out
    assert "extract_json" not in out
    assert "extract_schema_version" not in out


def test_strip_on_demand_client_cache_fields():
    out = {
        "video_id": VID,
        "extract_json": EXTRACT,
        "extract_schema_version": EXTRACT_JSON_SCHEMA_VERSION,
    }
    _strip_on_demand_client_cache_fields(out)
    assert "extract_json" not in out
    assert "extract_schema_version" not in out
    assert out["video_id"] == VID


def test_cache_hit_strips_extract_json():
    cached = _fresh_basic_cached()
    cached["narrative_vi"] = {"van_de_chinh": "cached deep"}
    sb = _service_sb_with_basic_row(cached)
    hit = _try_on_demand_cache_hit(sb, URL, analysis_depth="basic")
    assert hit is not None
    assert "extract_json" not in hit
    assert "extract_schema_version" not in hit


def test_basic_without_extract_json_returns_none():
    sb = _service_sb_with_basic_row(_fresh_basic_cached(with_extract=False))
    assert _try_on_demand_basic_upgrade_source(sb, URL) is None


def test_run_on_demand_deep_uses_upgrade_before_fetch():
    sb = _service_sb_with_basic_row(_fresh_basic_cached())
    user_sb = MagicMock()
    upgrade_out = {
        "video_id": VID,
        "__narrative_analysis": EXTRACT,
        "__analysis_depth": "deep",
    }
    with patch(
        "getviews_pipeline.video_analyze._try_on_demand_cache_hit",
        return_value=None,
    ), patch(
        "getviews_pipeline.video_analyze._try_on_demand_basic_upgrade_source",
        return_value=upgrade_out,
    ) as upgrade_mock, patch(
        "getviews_pipeline.video_analyze._fetch_and_analyze_async",
    ) as fetch_mock:
        out = run_video_analyze_on_demand(
            sb,
            user_sb,
            tiktok_url=URL,
            analysis_depth="deep",
        )
    upgrade_mock.assert_called_once()
    fetch_mock.assert_not_called()
    assert out is upgrade_out


def test_persist_on_demand_cache_stores_extract_json():
    sb = MagicMock()
    upsert = MagicMock()
    sb.table.return_value.upsert = upsert
    response = {
        "video_id": VID,
        "meta": {"views": 1},
        "extract_json": EXTRACT,
        "extract_schema_version": EXTRACT_JSON_SCHEMA_VERSION,
    }
    _persist_on_demand_cache(
        sb,
        tiktok_url=URL,
        video_id=VID,
        response=response,
        analysis_depth="basic",
    )
    payload = upsert.call_args[0][0]
    assert payload["cached_response"]["extract_json"] == EXTRACT
