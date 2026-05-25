"""``copy_first_frame_to_thumbnail`` — 360w WebP user-facing thumb from frame[0]."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline import r2


@pytest.fixture(autouse=True)
def _r2_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r2, "R2_ACCOUNT_ID", "test-account")
    monkeypatch.setattr(r2, "R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setattr(r2, "R2_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setattr(r2, "R2_PUBLIC_URL", "https://r2.test")
    monkeypatch.setattr(r2, "R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(r2, "_ffmpeg_available", lambda: True)


def test_returns_none_when_r2_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(r2, "R2_PUBLIC_URL", "")
    assert r2.copy_first_frame_to_thumbnail("v1") is None


def test_transcodes_frame_to_webp_and_returns_public_url(tmp_path: Path) -> None:
    fake_client = MagicMock()
    webp_bytes = b"RIFF....WEBP"

    def _fake_transcode(src: Path, dst: Path, **kwargs: object) -> bool:
        dst.write_bytes(webp_bytes)
        return True

    with patch.object(r2, "_get_r2_client", return_value=fake_client), \
         patch.object(r2, "r2_object_exists", side_effect=lambda key: key.endswith("0.png")), \
         patch.object(r2, "_download_r2_object_to_path", return_value=True), \
         patch.object(r2, "_ffmpeg_transcode_to_webp", side_effect=_fake_transcode):
        url = r2.copy_first_frame_to_thumbnail("vid-123")

    assert url == "https://r2.test/thumbnails/vid-123.webp"
    put = fake_client.put_object.call_args.kwargs
    assert put["Key"] == "thumbnails/vid-123.webp"
    assert put["ContentType"] == "image/webp"
    assert put["Body"] == webp_bytes
    fake_client.delete_object.assert_any_call(Bucket="test-bucket", Key="thumbnails/vid-123.png")
    fake_client.delete_object.assert_any_call(Bucket="test-bucket", Key="thumbnails/vid-123.jpg")


def test_falls_back_to_legacy_png_when_frame_missing() -> None:
    seen_keys: list[str] = []

    def _exists(key: str) -> bool:
        seen_keys.append(key)
        return key == "thumbnails/vid-123.png"

    with patch.object(r2, "r2_object_exists", side_effect=_exists), \
         patch.object(r2, "_download_r2_object_to_path", return_value=True) as dl, \
         patch.object(r2, "_transcode_local_image_to_webp_thumbnail", return_value="https://r2.test/thumbnails/vid-123.webp"):
        out = r2.copy_first_frame_to_thumbnail("vid-123")

    assert out == "https://r2.test/thumbnails/vid-123.webp"
    dl.assert_called_once()
    assert dl.call_args[0][0] == "thumbnails/vid-123.png"


def test_returns_none_when_no_source_keys() -> None:
    with patch.object(r2, "r2_object_exists", return_value=False):
        assert r2.copy_first_frame_to_thumbnail("vid-missing") is None


def test_upload_thumbnail_bytes_transcodes_to_webp() -> None:
    fake_client = MagicMock()
    webp_bytes = b"RIFF....WEBP"

    def _fake_transcode(src: Path, dst: Path, **kwargs: object) -> bool:
        dst.write_bytes(webp_bytes)
        return True

    with patch.object(r2, "_get_r2_client", return_value=fake_client), \
         patch.object(r2, "_ffmpeg_transcode_to_webp", side_effect=_fake_transcode):
        url = r2.upload_thumbnail_bytes("vid-abc", b"\xff\xd8\xff", "image/jpeg")

    assert url == "https://r2.test/thumbnails/vid-abc.webp"
    fake_client.put_object.assert_called_once()
    assert fake_client.put_object.call_args.kwargs["Key"] == "thumbnails/vid-abc.webp"
