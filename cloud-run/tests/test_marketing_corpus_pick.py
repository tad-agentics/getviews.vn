"""Marketing corpus pick orchestrator."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.marketing_corpus_pick import (
    ANALYSIS_FAILED,
    POOL_EXHAUSTED,
    build_marketing_pick_response,
    run_marketing_corpus_pick,
    select_marketing_corpus_video_row,
)


def test_select_marketing_corpus_video_row_parses_dict() -> None:
    sb = MagicMock()
    sb.rpc.return_value.execute.return_value = SimpleNamespace(
        data={
            "video_id": "7123",
            "tiktok_url": "https://www.tiktok.com/@x/video/7123",
            "creator_niche_id": 3,
            "priority_weight": 3,
        },
    )
    row = select_marketing_corpus_video_row(sb)
    assert row["video_id"] == "7123"
    sb.rpc.assert_called_with("select_marketing_corpus_video")


def test_build_marketing_pick_response_shapes_analysis() -> None:
    out = build_marketing_pick_response(
        {
            "video_id": "v1",
            "tiktok_url": "https://tiktok.com/v1",
            "creator_niche_id": 3,
            "creator_niche_slug": "food",
            "creator_niche_name_vn": "Ẩm thực",
            "priority_weight": 3,
            "views": 200_000,
        },
        {
            "mode": "win",
            "narrative_vi": {"van_de_chinh": "Hook yếu"},
            "diagnosis": "md",
            "performance_tier": "hit",
            "meta": {"creator": "@chef", "views": 200_000},
        },
        picked_at="2026-05-28T00:00:00Z",
    )
    assert out["video_id"] == "v1"
    assert out["creator_niche"]["slug"] == "food"
    assert out["analysis"]["narrative_vi"]["van_de_chinh"] == "Hook yếu"
    assert out["picked_at"] == "2026-05-28T00:00:00Z"


@patch("getviews_pipeline.marketing_corpus_pick.record_marketing_pick")
@patch("getviews_pipeline.marketing_corpus_pick.run_video_analyze_pipeline")
@patch("getviews_pipeline.marketing_corpus_pick.get_service_client")
def test_run_marketing_corpus_pick_records_on_success(
    mock_client: MagicMock,
    mock_pipeline: MagicMock,
    mock_record: MagicMock,
) -> None:
    sb = MagicMock()
    mock_client.return_value = sb
    sb.rpc.return_value.execute.return_value = SimpleNamespace(
        data={
            "video_id": "999",
            "tiktok_url": "https://www.tiktok.com/@a/video/999",
            "creator_niche_id": 1,
            "priority_weight": 3,
            "views": 150_000,
        },
    )
    mock_pipeline.return_value = {
        "video_id": "999",
        "mode": "win",
        "narrative_vi": {"van_de_chinh": "Vấn đề chính"},
        "meta": {"views": 150_000},
    }
    mock_record.return_value = "2026-05-28T12:00:00+00:00"

    result = run_marketing_corpus_pick()

    assert result["video_id"] == "999"
    mock_record.assert_called_once()
    mock_pipeline.assert_called_once()


@patch("getviews_pipeline.marketing_corpus_pick.record_marketing_pick")
@patch("getviews_pipeline.marketing_corpus_pick.finalize_video_narrative_layer")
@patch("getviews_pipeline.marketing_corpus_pick.run_video_analyze_pipeline")
@patch("getviews_pipeline.marketing_corpus_pick.get_service_client")
def test_run_marketing_corpus_pick_finalize_stale_cache(
    mock_client: MagicMock,
    mock_pipeline: MagicMock,
    mock_finalize: MagicMock,
    mock_record: MagicMock,
) -> None:
    sb = MagicMock()
    mock_client.return_value = sb
    sb.rpc.return_value.execute.return_value = SimpleNamespace(
        data={
            "video_id": "777",
            "tiktok_url": "https://www.tiktok.com/@b/video/777",
            "creator_niche_id": 4,
            "priority_weight": 2,
        },
    )
    mock_pipeline.return_value = {
        "video_id": "777",
        "narrative_vi": {},
        "__narrative_analysis": "cached",
    }

    def _fill_narrative(out: dict, **_kwargs: object) -> None:
        out["narrative_vi"] = {"van_de_chinh": "Sau finalize"}

    mock_finalize.side_effect = _fill_narrative
    mock_record.return_value = "2026-05-28T12:00:00+00:00"

    result = run_marketing_corpus_pick()

    assert result["analysis"]["narrative_vi"]["van_de_chinh"] == "Sau finalize"
    mock_finalize.assert_called_once()


@patch("getviews_pipeline.marketing_corpus_pick.finalize_video_narrative_layer")
@patch("getviews_pipeline.marketing_corpus_pick.run_video_analyze_pipeline")
@patch("getviews_pipeline.marketing_corpus_pick.get_service_client")
def test_run_marketing_corpus_pick_fails_without_narrative(
    mock_client: MagicMock,
    mock_pipeline: MagicMock,
    mock_finalize: MagicMock,
) -> None:
    sb = MagicMock()
    mock_client.return_value = sb
    sb.rpc.return_value.execute.return_value = SimpleNamespace(
        data={
            "video_id": "888",
            "creator_niche_id": 2,
            "priority_weight": 3,
        },
    )
    mock_pipeline.return_value = {"video_id": "888", "narrative_vi": None}
    mock_finalize.side_effect = lambda out, **_kwargs: None

    with pytest.raises(RuntimeError, match=ANALYSIS_FAILED):
        run_marketing_corpus_pick()


@patch("getviews_pipeline.marketing_corpus_pick.get_service_client")
def test_run_marketing_corpus_pick_pool_exhausted(mock_client: MagicMock) -> None:
    sb = MagicMock()
    mock_client.return_value = sb
    sb.rpc.return_value.execute.side_effect = Exception("marketing_pool_exhausted")

    with pytest.raises(RuntimeError, match=POOL_EXHAUSTED):
        run_marketing_corpus_pick()
