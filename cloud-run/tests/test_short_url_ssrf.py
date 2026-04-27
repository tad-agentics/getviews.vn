"""SSRF guard for ``_resolve_short_url``.

The short-link resolver must never follow a redirect chain to an
internal / metadata host. Each hop's ``Location`` is checked against
the TikTok host allowlist before we issue the next request.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from getviews_pipeline.routers.intent import _resolve_short_url


def _redirect_response(location: str, status_code: int = 302) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {"location": location}
    return resp


def _terminal_response(url: str) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.headers = {}
    resp.url = url
    return resp


def test_resolve_short_url_accepts_tiktok_redirect():
    """Standard short-link → www.tiktok.com video URL resolves end-to-end."""
    final_url = "https://www.tiktok.com/@foo/video/12345"
    head_responses = [_redirect_response(final_url), _terminal_response(final_url)]

    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.head.side_effect = head_responses

    with patch("getviews_pipeline.routers.intent.httpx.Client", return_value=fake_client):
        result = _resolve_short_url("https://vm.tiktok.com/abc123/")

    assert result == final_url


def test_resolve_short_url_blocks_metadata_redirect():
    """SSRF: a short link redirecting to GCP/AWS metadata must be rejected."""
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.head.return_value = _redirect_response("http://169.254.169.254/latest/meta-data/")

    short_url = "https://vm.tiktok.com/abc123/"
    with patch("getviews_pipeline.routers.intent.httpx.Client", return_value=fake_client):
        result = _resolve_short_url(short_url)

    # Returns original input unchanged → downstream pipelines reject as
    # non-TikTok URL with the standard "Thiếu URL TikTok hợp lệ" error.
    assert result == short_url


def test_resolve_short_url_blocks_internal_host_redirect():
    """SSRF: redirect to internal RFC1918 host must be rejected."""
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.head.return_value = _redirect_response("http://10.0.0.5:8080/admin")

    short_url = "https://vm.tiktok.com/abc123/"
    with patch("getviews_pipeline.routers.intent.httpx.Client", return_value=fake_client):
        result = _resolve_short_url(short_url)

    assert result == short_url


def test_resolve_short_url_blocks_arbitrary_external_host():
    """SSRF: redirect to attacker-controlled domain must be rejected."""
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.head.return_value = _redirect_response("https://evil.example.com/x")

    short_url = "https://vm.tiktok.com/abc123/"
    with patch("getviews_pipeline.routers.intent.httpx.Client", return_value=fake_client):
        result = _resolve_short_url(short_url)

    assert result == short_url


def test_resolve_short_url_no_redirect_returns_original():
    """A 200 with no Location header just returns the requested URL."""
    short_url = "https://vm.tiktok.com/abc123/"
    fake_client = MagicMock()
    fake_client.__enter__.return_value = fake_client
    fake_client.__exit__.return_value = False
    fake_client.head.return_value = _terminal_response(short_url)

    with patch("getviews_pipeline.routers.intent.httpx.Client", return_value=fake_client):
        result = _resolve_short_url(short_url)

    assert result == short_url
