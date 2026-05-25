"""Class-first reference pool resolution for ``run_video_diagnosis`` (compare path)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_reference_pool_class_ids_from_corpus_row() -> None:
    from getviews_pipeline.pipelines import _reference_pool_class_ids

    session: dict = {"_niche_ids": {"thời trang": 3}}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={
            "content_class_id": 42,
            "content_format": "product_review",
            "niche_id": 3,
        }
    )

    with patch("getviews_pipeline.pipelines.get_service_client", return_value=mock_client):
        cc, legacy = await _reference_pool_class_ids(
            session,
            niche="Thời trang",
            video_id="7123456789",
            legacy_niche_id_hint=None,
        )

    assert legacy == 3
    assert cc == 42


@pytest.mark.asyncio
async def test_reference_pool_class_ids_derives_from_format_when_cc_missing() -> None:
    from getviews_pipeline.pipelines import _reference_pool_class_ids

    session: dict = {}
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={
            "content_class_id": None,
            "content_format": "product_review",
            "niche_id": 3,
        }
    )

    with patch("getviews_pipeline.pipelines.get_service_client", return_value=mock_client):
        with patch(
            "getviews_pipeline.pipelines.content_class_id_for_reference_pool",
            return_value=99,
        ):
            cc, legacy = await _reference_pool_class_ids(
                session,
                niche="Thời trang",
                video_id="7123456789",
                legacy_niche_id_hint=3,
            )

    assert legacy == 3
    assert cc == 99


@pytest.mark.asyncio
async def test_derive_class_after_user_analysis() -> None:
    from getviews_pipeline.pipelines import _derive_class_after_user_analysis

    user_res = {"analysis": {"content_arc": "tutorial", "hook_analysis": {"hook_type": "question"}}}
    with patch(
        "getviews_pipeline.pipelines.classify_format",
        return_value="product_review",
    ):
        with patch(
            "getviews_pipeline.pipelines.content_class_id_for_reference_pool",
            return_value=55,
        ):
            cc, nid = await _derive_class_after_user_analysis(
                user_res,
                {},
                niche="Thời trang",
                legacy_niche_id=3,
            )
    assert cc == 55
    assert nid == 3
