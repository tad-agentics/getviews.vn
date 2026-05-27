"""finalize-lite / on-demand cache embed tile repair."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from getviews_pipeline.gemini import EMBED_CONTRACT_VERSION, count_valid_embedded_tiles
from getviews_pipeline.video_analyze import (
    ON_DEMAND_RESPONSE_SCHEMA_VERSION,
    _apply_embed_tile_repair_to_out,
    _response_needs_embed_tile_repair,
    _try_on_demand_cache_hit,
)


def _poisoned_cached_response() -> dict:
    return {
        "video_id": "7634391245737053447",
        "response_schema_version": 2,
        "source": "on_demand",
        "_schema_version": "v5",
        "reference_videos": [
            {
                "aweme_id": "111",
                "desc": "đồng hồ nam",
                "content_proximity_score": 2,
                "thumbnail_url": "https://thumb/111.jpg",
                "tiktok_url": "https://tiktok.com/@x/video/111",
                "views": 1000,
            },
        ],
        "narrative_vi": {
            "van_de_chinh": "Vấn đề chính prose đủ dài để hiển thị.",
            "diagnosis_vi": {
                "headline_vi": "Tiêu đề",
                "sections": [
                    {"section_id": "diagnosis", "text_vi": "Nội dung", "embedded_tiles": []},
                ],
            },
        },
    }


def test_response_needs_embed_tile_repair_when_refs_but_no_tiles() -> None:
    out = _poisoned_cached_response()
    assert _response_needs_embed_tile_repair(out) is True


def test_apply_embed_tile_repair_injects_tiles() -> None:
    out = _poisoned_cached_response()
    assert _apply_embed_tile_repair_to_out(out) is True
    diag = out["narrative_vi"]["diagnosis_vi"]
    assert count_valid_embedded_tiles(diag) >= 1
    assert out["embed_contract_version"] == EMBED_CONTRACT_VERSION
    assert out["response_schema_version"] == ON_DEMAND_RESPONSE_SCHEMA_VERSION


def test_try_on_demand_cache_hit_repairs_poisoned_blob() -> None:
    cached = _poisoned_cached_response()
    row = {
        "cached_response": cached,
        "computed_at": "2099-01-01T00:00:00+00:00",
    }
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[row],
    )

    with (
        patch("getviews_pipeline.video_analyze._diagnostics_fresh", return_value=True),
        patch(
            "getviews_pipeline.video_analyze._persist_on_demand_cache",
        ) as mock_persist,
    ):
        hit = _try_on_demand_cache_hit(mock_sb, "https://www.tiktok.com/@x/video/7634391245737053447")

    assert hit is not None
    diag = hit["narrative_vi"]["diagnosis_vi"]
    assert count_valid_embedded_tiles(diag) >= 1
    assert hit["embed_contract_version"] == EMBED_CONTRACT_VERSION
    mock_persist.assert_called_once()
