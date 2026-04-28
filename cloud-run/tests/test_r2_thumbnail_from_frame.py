"""``copy_first_frame_to_thumbnail`` — derive the user-facing video
thumbnail from the already-uploaded analysis frame[0].

Architecture principle: one heavy CDN pull per video, ever. The
video binary is downloaded once during ``corpus_ingest``; from
that single download we extract every visual asset we need (incl.
the thumbnail) and never hotlink the platform CDN again.

This helper is the second-half of that principle for thumbnails:
``frames/{video_id}/0.png`` is uploaded to R2 by ``upload_frames``
during the same in-flight ingest; here we issue one R2 ``copy_object``
op (no GB transfer, no local file read) to clone it to
``thumbnails/{video_id}.png`` so the FE has a stable, namespace-
clean URL.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from getviews_pipeline import r2


@pytest.fixture(autouse=True)
def _r2_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force ``r2_configured()`` true so the helper actually attempts the copy."""
    monkeypatch.setattr(r2, "R2_ACCOUNT_ID", "test-account")
    monkeypatch.setattr(r2, "R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setattr(r2, "R2_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setattr(r2, "R2_PUBLIC_URL", "https://r2.test")
    monkeypatch.setattr(r2, "R2_BUCKET_NAME", "test-bucket")


def test_returns_none_when_r2_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """No R2 credentials → skip silently (corpus ingest stays running)."""
    monkeypatch.setattr(r2, "R2_PUBLIC_URL", "")
    assert r2.copy_first_frame_to_thumbnail("v1") is None


def test_copies_with_correct_keys_and_returns_public_url() -> None:
    """Successful copy → returns ``{R2_PUBLIC_URL}/thumbnails/{id}.png``."""
    fake_client = MagicMock()
    with patch.object(r2, "_get_r2_client", return_value=fake_client):
        url = r2.copy_first_frame_to_thumbnail("vid-123")
    assert url == "https://r2.test/thumbnails/vid-123.png"
    fake_client.copy_object.assert_called_once()
    call = fake_client.copy_object.call_args.kwargs
    assert call["Bucket"] == "test-bucket"
    assert call["Key"] == "thumbnails/vid-123.png"
    assert call["CopySource"] == {"Bucket": "test-bucket", "Key": "frames/vid-123/0.png"}
    # MetadataDirective REPLACE so our explicit ContentType + CacheControl
    # win over whatever the source frame had.
    assert call["MetadataDirective"] == "REPLACE"
    assert call["ContentType"] == "image/png"
    assert "immutable" in call["CacheControl"]


def test_returns_none_on_clienterror_and_keeps_ingest_running() -> None:
    """R2 SDK raises (e.g. source-key NoSuchKey because frame upload
    failed earlier) → return None, do NOT raise. Ingest continues
    and the row falls back to the platform CDN URL via the caller."""
    fake_client = MagicMock()
    fake_client.copy_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "src missing"}}, "CopyObject",
    )
    with patch.object(r2, "_get_r2_client", return_value=fake_client):
        out = r2.copy_first_frame_to_thumbnail("vid-missing-frame")
    assert out is None


def test_returns_none_on_unexpected_exception() -> None:
    """Defensive — a non-boto exception from ``_get_r2_client`` etc.
    must not bubble out of the helper either."""
    with patch.object(r2, "_get_r2_client", side_effect=RuntimeError("boom")):
        out = r2.copy_first_frame_to_thumbnail("vid-1")
    assert out is None


def test_destination_key_uses_frame_extension_constant() -> None:
    """Sanity: the destination filename must follow ``_FRAME_EXT``,
    not be hard-coded — so a future format swap (.webp) propagates."""
    fake_client = MagicMock()
    with patch.object(r2, "_get_r2_client", return_value=fake_client):
        url = r2.copy_first_frame_to_thumbnail("v")
    assert url is not None
    assert url.endswith(r2._FRAME_EXT)
