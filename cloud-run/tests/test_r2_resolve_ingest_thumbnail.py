"""``resolve_ingest_thumbnail_url`` — WebP promotion on corpus re-upsert."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from getviews_pipeline import r2


@pytest.mark.asyncio
async def test_skips_when_webp_exists_patches_legacy_png_db_url() -> None:
    with patch.object(r2, "r2_public_thumbnail_exists", return_value=True), patch.object(
        r2,
        "r2_public_thumbnail_url",
        return_value="https://pub-abc.r2.dev/thumbnails/vid1.webp",
    ), patch.object(r2, "copy_first_frame_to_thumbnail") as frame_copy, patch.object(
        r2, "download_and_upload_thumbnail", new_callable=AsyncMock
    ) as cdn_mirror:
        out = await r2.resolve_ingest_thumbnail_url(
            "vid1",
            "https://pub-abc.r2.dev/thumbnails/vid1.png",
        )

    assert out == "https://pub-abc.r2.dev/thumbnails/vid1.webp"
    frame_copy.assert_not_called()
    cdn_mirror.assert_not_awaited()


@pytest.mark.asyncio
async def test_promotes_legacy_r2_png_via_frame_transcode() -> None:
    with patch.object(r2, "r2_public_thumbnail_exists", return_value=False), patch.object(
        r2,
        "copy_first_frame_to_thumbnail",
        return_value="https://pub-abc.r2.dev/thumbnails/vid2.webp",
    ) as frame_copy, patch.object(
        r2, "download_and_upload_thumbnail", new_callable=AsyncMock
    ) as cdn_mirror:
        out = await r2.resolve_ingest_thumbnail_url(
            "vid2",
            "https://pub-abc.r2.dev/thumbnails/vid2.png",
        )

    assert out == "https://pub-abc.r2.dev/thumbnails/vid2.webp"
    frame_copy.assert_called_once_with("vid2")
    cdn_mirror.assert_not_awaited()


@pytest.mark.asyncio
async def test_cdn_mirror_only_for_non_r2_platform_url() -> None:
    cdn_mirror = AsyncMock(return_value="https://pub-abc.r2.dev/thumbnails/vid3.webp")
    with patch.object(r2, "r2_public_thumbnail_exists", return_value=False), patch.object(
        r2, "copy_first_frame_to_thumbnail", return_value=None
    ), patch.object(r2, "download_and_upload_thumbnail", cdn_mirror):
        out = await r2.resolve_ingest_thumbnail_url(
            "vid3",
            "https://p16-sign.tiktokcdn.com/cover.jpg",
        )

    assert out == "https://pub-abc.r2.dev/thumbnails/vid3.webp"
    cdn_mirror.assert_awaited_once_with(
        "https://p16-sign.tiktokcdn.com/cover.jpg",
        "vid3",
    )


@pytest.mark.asyncio
async def test_phantom_r2_png_does_not_hit_cdn_mirror() -> None:
    cdn_mirror = AsyncMock()
    with patch.object(r2, "r2_public_thumbnail_exists", return_value=False), patch.object(
        r2, "copy_first_frame_to_thumbnail", return_value=None
    ), patch.object(r2, "download_and_upload_thumbnail", cdn_mirror):
        out = await r2.resolve_ingest_thumbnail_url(
            "vid4",
            "https://pub-abc.r2.dev/thumbnails/vid4.png",
        )

    assert out is None
    cdn_mirror.assert_not_awaited()


def test_is_r2_pub_thumbnail_db_url() -> None:
    assert r2.is_r2_pub_thumbnail_db_url(
        "https://pub-abc.r2.dev/thumbnails/vid.png",
    )
    assert not r2.is_r2_pub_thumbnail_db_url(
        "https://p16-sign.tiktokcdn.com/cover.jpg",
    )
    assert not r2.is_r2_pub_thumbnail_db_url(None)
