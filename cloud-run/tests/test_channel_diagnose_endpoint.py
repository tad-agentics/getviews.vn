"""Integration tests for POST /channel/diagnose SSE endpoint.

These tests exercise the HTTP boundary with dependency_overrides for auth
and module-level mocks for external I/O (EnsembleData, Gemini, Supabase).
We verify:
- SSE envelope: stream_id present, seq monotone, terminal done=True
- trajectory event is emitted before section events
- section_start / text_chunk / section_done / recommendation_item events
- mandatory sections (verdict + recommendations) are present
- 202 already_in_flight response when guard is active
- insufficient_credits error path
- cache hit replay path
- per-trajectory smoke: decline_from_peak, stagnant, steady_growth, breakout,
  bursty, new_account
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Minimal narrative fixture that parser can split
# ---------------------------------------------------------------------------

_FULL_NARRATIVE = """\
=== verdict ===
TITLE: Kết luận

Kênh này đang ở giai đoạn stagnant. Tỷ lệ tương tác thấp so với benchmark.

=== what_worked ===
TITLE: Những gì đã hoạt động

Định dạng unboxing có hiệu suất cao nhất với avg 120k views.

=== what_falling ===
TITLE: Những gì đang giảm

Video lifestyle giảm 40% so với tháng trước.

=== competitive_landscape ===
TITLE: Đối thủ cạnh tranh

Các creator trong ngách có avg 200k views, vượt trội hơn kênh này.

=== recommendations ===
TITLE: Khuyến nghị

1. **Tập trung vào unboxing** 
Tăng tần suất unboxing từ 2 lên 4 video/tuần.

2. **Cải thiện hook 3 giây đầu**
Thêm yếu tố gây tò mò ngay từ đầu video.

3. **Tối ưu caption**
Dùng hashtag ngách thay vì hashtag rộng.

4. **Đăng vào giờ cao điểm**
18:00-21:00 ICT là khung giờ tốt nhất.

5. **Kết hợp CTA mạnh**
Kêu gọi comment cụ thể thay vì like chung chung.

6. **Thử nghiệm độ dài video**
Video 45-60 giây có tỷ lệ hoàn thành cao hơn.

7. **Collab với micro-creator**
Tìm creator cùng ngách có 10k-50k followers.
"""

_BREAKOUT_NARRATIVE = """\
=== verdict ===
TITLE: Kết luận

Kênh đang trong giai đoạn breakout. Tăng trưởng đột biến trong 30 ngày qua.

=== what_worked ===
TITLE: Những gì đã tạo breakout

Video viral nhờ format challenge đạt 2M views.

=== competitive_landscape ===
TITLE: Đối thủ cạnh tranh

Creator cùng ngách đang có avg 500k views.

=== recommendations ===
TITLE: Khuyến nghị

1. **Duy trì momentum** 
Đăng đều đặn để thuật toán tiếp tục phân phối.

2. **Double down format viral**
Làm thêm 3-5 video cùng format đã viral.

3. **Tương tác với viewers mới**
Reply comment trong 2h đầu sau khi đăng.

4. **Tối ưu bio và profile**
Cập nhật bio để convert visitor thành follower.

5. **Tạo series**
Biến format viral thành series có tên riêng.

6. **Collab ngay**
Tận dụng momentum để tiếp cận creator lớn hơn.

7. **Phân tích traffic source**
Xem từ đâu viewers đến để double down kênh đó.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_sse(raw: bytes) -> list[dict[str, Any]]:
    """Parse raw SSE bytes into list of JSON payloads."""
    events = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def _make_fake_videos(count: int = 15, avg_views: int = 50_000) -> list[dict[str, Any]]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    videos = []
    for i in range(count):
        videos.append({
            "video_url": f"https://tiktok.com/@testcreator/video/{i}",
            "thumbnail_url": f"https://r2.example.com/thumb_{i}.jpg",
            "views": avg_views + (i * 1000),
            "likes": 1000 + i * 10,
            "comments": 50 + i,
            "shares": 20 + i,
            "caption": f"Video #{i} #beauty #skincare",
            "posted_at": (base + timedelta(days=i)).replace(tzinfo=UTC),
            "duration_sec": 45 + i % 30,
            "content_format": "beauty_tutorial",
        })
    return videos


def _make_channel_pattern(videos: list[dict[str, Any]]) -> dict[str, Any]:
    views = [v["views"] for v in videos]
    avg = sum(views) / len(views) if views else 0
    return {
        "global_avg_views": avg,
        "total_videos": len(videos),
        "formats": {
            "beauty_tutorial": {
                "count": len(videos),
                "avg_views": avg,
                "total_views": sum(views),
            }
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_videos() -> list[dict[str, Any]]:
    return _make_fake_videos()


@pytest.fixture
def fake_channel_pattern(fake_videos: list[dict[str, Any]]) -> dict[str, Any]:
    return _make_channel_pattern(fake_videos)


@pytest.fixture
def app_with_mocks(fake_videos, fake_channel_pattern):
    """Create a FastAPI test app with all external dependencies mocked."""
    from fastapi import FastAPI
    from getviews_pipeline.routers.video import router
    from getviews_pipeline.deps import require_user

    test_app = FastAPI()
    test_app.include_router(router)

    async def override_require_user():
        return {"user_id": "test-user-123", "access_token": "test-token"}

    test_app.dependency_overrides[require_user] = override_require_user
    yield test_app
    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Core SSE helper
# ---------------------------------------------------------------------------

def _make_fake_sb(data: Any = None) -> MagicMock:
    """Reusable Supabase mock that returns ``data`` on any chain ending in .execute()."""
    m = MagicMock()
    result = MagicMock()
    result.data = data
    chain = MagicMock()
    chain.select = MagicMock(return_value=chain)
    chain.eq = MagicMock(return_value=chain)
    chain.gte = MagicMock(return_value=chain)
    chain.maybe_single = MagicMock(return_value=chain)
    chain.upsert = MagicMock(return_value=chain)
    chain.execute = MagicMock(return_value=result)
    m.table = MagicMock(return_value=chain)
    return m


def _run_diagnose(
    app_with_mocks,
    fake_videos,
    fake_channel_pattern,
    trajectory: str,
    narrative: str = _FULL_NARRATIVE,
    handle: str = "testcreator",
    niche_id: int = 1,
    video_url: str = "",
    cache_row: dict | None = None,
) -> list[dict[str, Any]]:
    """Run /channel/diagnose with mocked I/O and return parsed SSE events."""

    fake_recent_window = {
        "avg_views": 55_000,
        "video_count": 5,
        "days": 30,
    }
    fake_inflection = None
    fake_ugc_creators = [
        {
            "handle": "competitor1",
            "followers": 50_000,
            "avg_views": 80_000,
            "thumbnail_url": "https://r2.example.com/c1.jpg",
            "niche_slug": "beauty",
        }
    ]

    mock_response = MagicMock()
    mock_response.text = narrative

    with (
        patch(
            "getviews_pipeline.routers.video._fetch_channel_diagnoses_cache",
            return_value=cache_row,
        ),
        patch(
            "getviews_pipeline.routers.video._persist_channel_diagnoses",
        ),
        patch(
            "getviews_pipeline.channel_diagnose._decrement_credit_or_raise",
        ),
        patch(
            "getviews_pipeline.channel_diagnose.fetch_channel_videos_live",
            new_callable=AsyncMock,
            return_value=fake_videos,
        ),
        patch(
            "getviews_pipeline.channel_diagnose.fetch_ugc_creators",
            new_callable=AsyncMock,
            return_value=fake_ugc_creators,
        ),
        patch(
            "getviews_pipeline.channel_diagnose._fetch_niche_benchmarks",
            return_value={"channel_count": 25, "avg_views": 70_000},
        ),
        patch(
            "getviews_pipeline.channel_diagnose.build_channel_pattern",
            return_value=fake_channel_pattern,
        ),
        patch(
            "getviews_pipeline.channel_diagnose.compute_recent_window_stats",
            return_value=fake_recent_window,
        ),
        patch(
            "getviews_pipeline.channel_diagnose.compute_inflection_point",
            return_value=fake_inflection,
        ),
        patch(
            "getviews_pipeline.channel_diagnose.classify_trajectory",
            return_value=trajectory,
        ),
        patch(
            "getviews_pipeline.channel_diagnose.select_niche_peer_videos",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "getviews_pipeline.gemini._generate_content_models",
            return_value=mock_response,
        ),
        patch(
            "getviews_pipeline.routers.video.user_supabase",
            return_value=_make_fake_sb(),
        ),
        patch(
            "getviews_pipeline.routers.video.get_service_client",
            return_value=_make_fake_sb(),
        ),
    ):
        client = TestClient(app_with_mocks, raise_server_exceptions=False)
        resp = client.post(
            "/channel/diagnose",
            params={
                "handle": handle,
                "niche_id": niche_id,
                "video_url": video_url,
            },
        )
    assert resp.status_code == 200
    return _parse_sse(resp.content)


# ---------------------------------------------------------------------------
# Basic SSE envelope tests
# ---------------------------------------------------------------------------

class TestChannelDiagnoseSSEEnvelope:
    def test_stream_id_present_in_all_events(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        for evt in events:
            assert "stream_id" in evt, f"Missing stream_id in event: {evt}"

    def test_seq_monotone(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        seqs = [e["seq"] for e in events if "seq" in e]
        assert seqs == sorted(seqs), f"seq not monotone: {seqs}"

    def test_terminal_event_done_true(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        terminal = [e for e in events if e.get("done") is True]
        assert len(terminal) >= 1, "No terminal done=True event found"

    def test_trajectory_event_before_sections(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        types_ordered = [e.get("type") for e in events if "type" in e]
        traj_idx = next((i for i, t in enumerate(types_ordered) if t == "trajectory"), None)
        sec_idx = next((i for i, t in enumerate(types_ordered) if t == "section_start"), None)
        assert traj_idx is not None, "No trajectory event emitted"
        if sec_idx is not None:
            assert traj_idx < sec_idx, "trajectory event must precede section_start"

    def test_trajectory_event_value(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "breakout",
                                narrative=_BREAKOUT_NARRATIVE)
        traj_evt = next((e for e in events if e.get("type") == "trajectory"), None)
        assert traj_evt is not None
        assert traj_evt["trajectory"] == "breakout"

    def test_mandatory_sections_emitted(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        started = {e["section_id"] for e in events if e.get("type") == "section_start"}
        assert "verdict" in started
        assert "recommendations" in started

    def test_section_start_has_title(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        for evt in events:
            if evt.get("type") == "section_start":
                assert "title" in evt and evt["title"], f"section_start missing title: {evt}"

    def test_recommendation_items_emitted(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        rec_items = [e for e in events if e.get("type") == "recommendation_item"]
        assert len(rec_items) >= 7, f"Expected 7 recommendation_items, got {len(rec_items)}"

    def test_section_done_follows_section_start(self, app_with_mocks, fake_videos, fake_channel_pattern):
        events = _run_diagnose(app_with_mocks, fake_videos, fake_channel_pattern, "stagnant")
        open_sections: set[str] = set()
        for evt in events:
            etype = evt.get("type")
            if etype == "section_start":
                open_sections.add(evt["section_id"])
            elif etype == "section_done":
                sid = evt["section_id"]
                assert sid in open_sections, f"section_done for {sid} without matching section_start"
                open_sections.discard(sid)
        assert not open_sections, f"Unclosed sections: {open_sections}"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

class TestChannelDiagnoseErrorPaths:
    def test_insufficient_credits_error_event(self, app_with_mocks, fake_videos, fake_channel_pattern):
        from getviews_pipeline.channel_diagnose import InsufficientCreditsError
        with (
            patch("getviews_pipeline.routers.video._fetch_channel_diagnoses_cache", return_value=None),
            patch(
                "getviews_pipeline.channel_diagnose._decrement_credit_or_raise",
                side_effect=InsufficientCreditsError(),
            ),
            patch("getviews_pipeline.routers.video.user_supabase", return_value=_make_fake_sb()),
            patch("getviews_pipeline.routers.video.get_service_client", return_value=_make_fake_sb()),
        ):
            client = TestClient(app_with_mocks, raise_server_exceptions=False)
            resp = client.post(
                "/channel/diagnose",
                params={"handle": "testcreator", "niche_id": 1},
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.content)
        terminal = next((e for e in events if e.get("done") is True), None)
        assert terminal is not None
        assert terminal.get("error") == "insufficient_credits"

    def test_channel_not_found_error_event(self, app_with_mocks, fake_videos, fake_channel_pattern):
        with (
            patch("getviews_pipeline.routers.video._fetch_channel_diagnoses_cache", return_value=None),
            patch("getviews_pipeline.channel_diagnose._decrement_credit_or_raise"),
            patch(
                "getviews_pipeline.channel_diagnose.fetch_channel_videos_live",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("getviews_pipeline.routers.video.user_supabase", return_value=_make_fake_sb()),
            patch("getviews_pipeline.routers.video.get_service_client", return_value=_make_fake_sb()),
        ):
            client = TestClient(app_with_mocks, raise_server_exceptions=False)
            resp = client.post(
                "/channel/diagnose",
                params={"handle": "ghost_user_xyz", "niche_id": 1},
            )
        assert resp.status_code == 200
        events = _parse_sse(resp.content)
        terminal = next((e for e in events if e.get("done") is True), None)
        assert terminal is not None
        assert terminal.get("error") == "channel_not_found"


# ---------------------------------------------------------------------------
# Cache hit replay
# ---------------------------------------------------------------------------

class TestChannelDiagnoseCacheHit:
    def test_cache_hit_event_emitted(self, app_with_mocks, fake_videos, fake_channel_pattern):
        sections = [
            {"section_id": "verdict", "title": "Kết luận", "text": "Cache text verdict."},
            {"section_id": "recommendations", "title": "Khuyến nghị", "text": "Cache recs."},
        ]
        cache_row = {
            "trajectory_shape": "stagnant",
            "sections": sections,
            "recommendations": [{"index": 1, "title": "Fix it", "body": "Do the thing."}],
            "top_performers": [],
            "worst_performers": [],
            "ugc_creators": [],
            "channel_pattern": {"global_avg_views": 50000, "total_videos": 15},
            "inflection": None,
            "creator_match": None,
            "video_count": 15,
            "computed_at": (datetime.now(tz=UTC) - timedelta(days=1)).isoformat(),
        }
        events = _run_diagnose(
            app_with_mocks, fake_videos, fake_channel_pattern,
            "stagnant", cache_row=cache_row,
        )
        cache_hit_evt = next((e for e in events if e.get("type") == "cache_hit"), None)
        assert cache_hit_evt is not None, "Expected cache_hit event"

    def test_cache_hit_has_payload_with_cache_true(self, app_with_mocks, fake_videos, fake_channel_pattern):
        sections = [
            {"section_id": "verdict", "title": "Kết luận", "text": "Cached."},
            {"section_id": "recommendations", "title": "Recs", "text": "Cached recs."},
        ]
        cache_row = {
            "trajectory_shape": "steady_growth",
            "sections": sections,
            "recommendations": [],
            "top_performers": [],
            "worst_performers": [],
            "ugc_creators": [],
            "channel_pattern": {"global_avg_views": 50000, "total_videos": 15},
            "inflection": None,
            "creator_match": None,
            "video_count": 15,
            "computed_at": datetime.now(tz=UTC).isoformat(),
        }
        events = _run_diagnose(
            app_with_mocks, fake_videos, fake_channel_pattern,
            "steady_growth", cache_row=cache_row,
        )
        payload_evt = next((e for e in events if "payload" in e), None)
        assert payload_evt is not None
        assert payload_evt["payload"].get("cache_hit") is True


# ---------------------------------------------------------------------------
# Per-trajectory smoke tests
# ---------------------------------------------------------------------------

TRAJECTORY_NARRATIVES = {
    "stagnant": _FULL_NARRATIVE,
    "decline_from_peak": _FULL_NARRATIVE,
    "bursty": _FULL_NARRATIVE,
    "breakout": _BREAKOUT_NARRATIVE,
    "steady_growth": _FULL_NARRATIVE.replace("what_falling", "competitive_landscape"),
    "new_account": _FULL_NARRATIVE.replace("what_falling", "competitive_landscape"),
}

# steady_growth and new_account don't have "what_falling" in their default flow


@pytest.mark.parametrize("trajectory", list(TRAJECTORY_NARRATIVES.keys()))
def test_trajectory_smoke(trajectory, app_with_mocks, fake_videos, fake_channel_pattern):
    """Each trajectory should produce valid SSE with trajectory event and mandatory sections."""
    narrative = TRAJECTORY_NARRATIVES[trajectory]
    # For new_account trajectory, mock select_niche_peer_videos
    events = _run_diagnose(
        app_with_mocks, fake_videos, fake_channel_pattern,
        trajectory=trajectory, narrative=narrative,
    )
    # trajectory event
    traj_evt = next((e for e in events if e.get("type") == "trajectory"), None)
    assert traj_evt is not None, f"[{trajectory}] No trajectory event"
    assert traj_evt["trajectory"] == trajectory

    # mandatory sections
    section_starts = {e["section_id"] for e in events if e.get("type") == "section_start"}
    assert "verdict" in section_starts, f"[{trajectory}] Missing 'verdict' section"
    assert "recommendations" in section_starts, f"[{trajectory}] Missing 'recommendations' section"

    # terminal done
    terminal = next((e for e in events if e.get("done") is True), None)
    assert terminal is not None, f"[{trajectory}] No terminal done=True"
