"""Phase 5.1.1 — unit tests for normalize_tiktok_url."""
import pytest
from getviews_pipeline.video_analyze import normalize_tiktok_url


@pytest.mark.parametrize(
    "raw,expected",
    [
        # http → https
        (
            "http://www.tiktok.com/@creator/video/123",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # missing www
        (
            "https://tiktok.com/@creator/video/123",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # trailing slash stripped
        (
            "https://www.tiktok.com/@creator/video/123/",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # query params stripped
        (
            "https://www.tiktok.com/@creator/video/123?_r=1&share_app_id=1233",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # fragment stripped
        (
            "https://www.tiktok.com/@creator/video/123#comments",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # all combined
        (
            "http://tiktok.com/@creator/video/123/?utm=abc#top",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # already canonical — no change
        (
            "https://www.tiktok.com/@creator/video/123",
            "https://www.tiktok.com/@creator/video/123",
        ),
        # vt.tiktok.com short links — keep netloc unchanged (can't resolve without HTTP)
        (
            "https://vt.tiktok.com/ZSM7abc/",
            "https://vt.tiktok.com/ZSM7abc",
        ),
        # vm.tiktok.com short links — keep netloc unchanged
        (
            "https://vm.tiktok.com/ZSM7abc/",
            "https://vm.tiktok.com/ZSM7abc",
        ),
        # empty string → empty string (no crash)
        ("", ""),
    ],
)
def test_normalize_tiktok_url(raw: str, expected: str) -> None:
    assert normalize_tiktok_url(raw) == expected
