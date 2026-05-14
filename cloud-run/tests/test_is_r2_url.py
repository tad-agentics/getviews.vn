"""Unit tests for ``_is_r2_url`` in corpus_context.

Verifies that the function correctly identifies permanent R2 URLs regardless
of whether the deployment uses the default Cloudflare r2.dev domain or a
custom domain configured via R2_PUBLIC_URL / R2_VIDEO_PUBLIC_URL.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


def _call(url: str | None, public_url: str = "", video_public_url: str = "") -> bool:
    with (
        patch("getviews_pipeline.config.R2_PUBLIC_URL", public_url),
        patch("getviews_pipeline.config.R2_VIDEO_PUBLIC_URL", video_public_url),
    ):
        from getviews_pipeline.corpus_context import _is_r2_url
        return _is_r2_url(url)


@pytest.mark.parametrize("url", [None, "", "   "])
def test_none_or_empty_returns_false(url: str | None) -> None:
    assert _call(url) is False


def test_default_pub_prefix_recognised() -> None:
    """Default Cloudflare r2.dev URLs must be treated as permanent even when
    R2_PUBLIC_URL is not configured."""
    assert _call("https://pub-abc123.r2.dev/thumbnails/vid1.png") is True


def test_custom_domain_recognised_via_R2_PUBLIC_URL() -> None:
    """Custom domain set as R2_PUBLIC_URL must be recognised as permanent."""
    assert _call(
        "https://media.getviews.vn/thumbnails/vid1.png",
        public_url="https://media.getviews.vn",
    ) is True


def test_r2_video_public_url_not_used_for_thumbnail_check() -> None:
    """R2_VIDEO_PUBLIC_URL must NOT be used to classify thumbnail URLs as permanent.

    Thumbnail write helpers always use R2_PUBLIC_URL; R2_VIDEO_PUBLIC_URL is for
    video clips only. A thumbnail_url starting with the video CDN domain would be
    a 404 or corrupted data — returning True here would silently skip its repair
    in refresh_stale_thumbnails.
    """
    assert _call(
        "https://video.getviews.vn/thumbnails/vid1.png",
        public_url="https://media.getviews.vn",
        video_public_url="https://video.getviews.vn",
    ) is False


def test_tiktok_cdn_url_not_r2() -> None:
    """TikTok CDN signed URLs must not be classified as permanent R2 URLs."""
    assert _call(
        "https://p16-sign-sg.tiktokcdn.com/obj/tos-alisg/abc?x-expire=123"
    ) is False


def test_tiktok_cdn_url_not_r2_with_custom_domain_configured() -> None:
    """When a custom domain is configured, TikTok CDN must still be non-R2."""
    assert _call(
        "https://p16-sign-sg.tiktokcdn.com/obj/tos-alisg/abc",
        public_url="https://media.getviews.vn",
    ) is False


def test_partial_prefix_match_not_classified_as_r2() -> None:
    """A URL that starts with a similar but different hostname must not match."""
    assert _call(
        "https://media.getviews.vn.evil.com/thumbnails/vid1.png",
        public_url="https://media.getviews.vn",
    ) is False


def test_both_public_urls_unconfigured_falls_back_to_pub_prefix() -> None:
    """When neither env var is set, only the https://pub- prefix is trusted."""
    assert _call("https://pub-xyz.r2.dev/frames/vid1/0.png") is True
    assert _call("https://other.example.com/frames/vid1/0.png") is False


def test_trailing_slash_in_R2_PUBLIC_URL_does_not_create_double_slash() -> None:
    """R2_PUBLIC_URL configured with a trailing slash must not produce //
    in the prefix check, which would cause valid R2 URLs to be misclassified
    as non-R2 and trigger unnecessary re-uploads (regression for the double-slash bug)."""
    assert _call(
        "https://media.getviews.vn/thumbnails/vid1.png",
        public_url="https://media.getviews.vn/",  # trailing slash
    ) is True


def test_exact_base_url_match_with_trailing_slash_configured() -> None:
    """url == R2_PUBLIC_URL (with trailing slash stripped) should still match."""
    assert _call(
        "https://media.getviews.vn",
        public_url="https://media.getviews.vn/",
    ) is True
