"""Wave 2.5 Phase A PR #3 — scene-frame extraction + R2 upload helpers.

Tests exercise the three new module-level functions in
``getviews_pipeline.r2``:

  extract_scene_frames        — ffmpeg shellout per scene midpoint
  upload_scene_frames         — boto3 put_object per extracted frame
  extract_and_upload_scene_frames  — async orchestrator + cleanup

All tests mock subprocess / boto3 / R2 config — no real ffmpeg, no
real R2 calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from getviews_pipeline.r2 import (
    _SCENE_FRAME_EXT,
    _SCENE_FRAME_MIN_TS,
    _scene_midpoint,
    extract_and_upload_scene_frames,
    extract_scene_frames,
    upload_scene_frames,
)

# ── _scene_midpoint clamping ─────────────────────────────────────────

def test_midpoint_of_positive_range() -> None:
    assert _scene_midpoint(1.0, 3.0) == 2.0


def test_midpoint_clamped_to_floor_when_scene_at_zero() -> None:
    """A scene starting at 0.0 should still return a seekable
    timestamp, not 0.0 — ffmpeg refuses to seek to 0 on some
    containers."""
    assert _scene_midpoint(0.0, 0.1) == _SCENE_FRAME_MIN_TS


def test_midpoint_never_below_floor() -> None:
    assert _scene_midpoint(0.0, 0.0) == _SCENE_FRAME_MIN_TS


# ── extract_scene_frames — graceful degradation ──────────────────────

def test_extract_returns_empty_when_ffmpeg_missing(tmp_path: Path) -> None:
    vid = tmp_path / "fake.mp4"
    vid.write_bytes(b"not-a-video")
    with patch("getviews_pipeline.r2._ffmpeg_available", return_value=False):
        result = extract_scene_frames(vid, "vid-1", [(0, 1.0), (1, 3.0)])
    assert result == []


def test_extract_returns_empty_when_video_missing(tmp_path: Path) -> None:
    vid = tmp_path / "does-not-exist.mp4"
    with patch("getviews_pipeline.r2._ffmpeg_available", return_value=True):
        result = extract_scene_frames(vid, "vid-1", [(0, 1.0)])
    assert result == []


def test_extract_success_path_returns_index_path_pairs(tmp_path: Path, monkeypatch) -> None:
    """Mock subprocess.run to simulate ffmpeg creating the output
    file; assert we get back the (index, path) pairs for successful
    extractions."""
    vid = tmp_path / "video.mp4"
    vid.write_bytes(b"fake-mp4-content")

    def fake_run(cmd, capture_output=True, timeout=None):
        # Extract the output path from the ffmpeg command — it's the
        # last argument. Create a file there so the caller's exists()
        # + size checks pass.
        out = Path(cmd[-1])
        out.write_bytes(b"fake-jpg-bytes" * 100)  # ~1400 bytes
        return MagicMock(returncode=0, stderr=b"")

    with patch("getviews_pipeline.r2._ffmpeg_available", return_value=True), \
         patch("subprocess.run", side_effect=fake_run):
        result = extract_scene_frames(
            vid, "vid-1", [(0, 1.0), (1, 3.5), (2, 6.2)],
        )

    assert len(result) == 3
    assert [pair[0] for pair in result] == [0, 1, 2]
    for idx, path in result:
        assert path.suffix == _SCENE_FRAME_EXT
        assert f"_{idx}" in path.name


def test_extract_retries_second_scale_when_first_ffmpeg_fails(tmp_path: Path) -> None:
    """First attempt (720p) can fail; second attempt (fallback width) may succeed."""
    vid = tmp_path / "video.mp4"
    vid.write_bytes(b"fake")
    call_n = {"n": 0}

    def fake_run(cmd, capture_output=True, timeout=None):
        call_n["n"] += 1
        out = Path(cmd[-1])
        if call_n["n"] == 1:
            return MagicMock(returncode=1, stderr=b"decode stall")
        out.write_bytes(b"fake-jpg-bytes" * 100)
        return MagicMock(returncode=0, stderr=b"")

    with patch("getviews_pipeline.r2._ffmpeg_available", return_value=True), \
         patch("subprocess.run", side_effect=fake_run):
        result = extract_scene_frames(
            vid, "vid-1", [(0, 1.0)],
        )

    assert len(result) == 1
    assert call_n["n"] == 2


def test_extract_skips_failed_ffmpeg_runs(tmp_path: Path) -> None:
    """ffmpeg returncode != 0 for one scene should not abort the
    others — we still get the other scenes back."""
    vid = tmp_path / "video.mp4"
    vid.write_bytes(b"fake")

    call_count = {"n": 0}

    def fake_run(cmd, capture_output=True, timeout=None):
        out = Path(cmd[-1])
        call_count["n"] += 1
        n = call_count["n"]
        # With primary+fallback, scene 1 (middle) must fail both attempts:
        # invocations 2 and 3 = 720p + fallback for the second scene.
        if n in (2, 3):
            return MagicMock(returncode=1, stderr=b"ffmpeg decoding error")
        out.write_bytes(b"jpg" * 100)
        return MagicMock(returncode=0, stderr=b"")

    with patch("getviews_pipeline.r2._ffmpeg_available", return_value=True), \
         patch("subprocess.run", side_effect=fake_run):
        result = extract_scene_frames(vid, "vid-1", [(0, 1.0), (1, 3.0), (2, 5.0)])

    # 3 scenes; middle scene fails both scale attempts → 2 successful
    assert len(result) == 2
    assert [i for i, _ in result] == [0, 2]


# ── upload_scene_frames — boto3 mock ─────────────────────────────────

def test_upload_returns_empty_when_r2_not_configured(tmp_path: Path) -> None:
    frame = tmp_path / "f.jpg"
    frame.write_bytes(b"jpg-bytes")
    with patch("getviews_pipeline.r2.r2_configured", return_value=False):
        result = upload_scene_frames("vid-1", [(0, frame)])
    assert result == []


def test_upload_key_pattern_is_video_shots_scene_index_jpg(tmp_path: Path) -> None:
    frame = tmp_path / "f.jpg"
    frame.write_bytes(b"jpg-bytes")

    client_mock = MagicMock()
    with patch("getviews_pipeline.r2.r2_configured", return_value=True), \
         patch("getviews_pipeline.r2._get_r2_client", return_value=client_mock), \
         patch("getviews_pipeline.r2.R2_PUBLIC_URL", "https://cdn.example.com", create=True), \
         patch("getviews_pipeline.r2.R2_BUCKET_NAME", "getviews", create=True):
        result = upload_scene_frames("vid-123", [(3, frame)])

    assert len(result) == 1
    scene_index, url = result[0]
    assert scene_index == 3
    assert url.endswith("video_shots/vid-123/3.jpg")
    # Boto3 put_object called with the right key
    kwargs = client_mock.put_object.call_args.kwargs
    assert kwargs["Key"] == "video_shots/vid-123/3.jpg"
    assert kwargs["ContentType"] == "image/jpeg"


def test_upload_continues_on_per_frame_boto_error(tmp_path: Path) -> None:
    """If boto3 errors on one frame, the others still upload."""
    from botocore.exceptions import ClientError

    frame1 = tmp_path / "f1.jpg"
    frame2 = tmp_path / "f2.jpg"
    frame1.write_bytes(b"jpg")
    frame2.write_bytes(b"jpg")

    client_mock = MagicMock()
    client_mock.put_object.side_effect = [
        ClientError({"Error": {"Code": "SignatureDoesNotMatch"}}, "put_object"),
        None,  # second succeeds
    ]

    with patch("getviews_pipeline.r2.r2_configured", return_value=True), \
         patch("getviews_pipeline.r2._get_r2_client", return_value=client_mock), \
         patch("getviews_pipeline.r2.R2_PUBLIC_URL", "https://cdn.example.com", create=True), \
         patch("getviews_pipeline.r2.R2_BUCKET_NAME", "getviews", create=True):
        result = upload_scene_frames("vid-1", [(0, frame1), (1, frame2)])

    # Only the second frame uploaded successfully
    assert len(result) == 1
    assert result[0][0] == 1


# ── extract_and_upload_scene_frames orchestrator ────────────────────

@pytest.mark.asyncio
async def test_orchestrator_empty_when_r2_not_configured(tmp_path: Path) -> None:
    with patch("getviews_pipeline.r2.r2_configured", return_value=False):
        out = await extract_and_upload_scene_frames(
            tmp_path / "v.mp4", "vid-1",
            [{"start": 0.0, "end": 2.0}],
        )
    assert out == []


@pytest.mark.asyncio
async def test_orchestrator_empty_when_no_scenes(tmp_path: Path) -> None:
    with patch("getviews_pipeline.r2.r2_configured", return_value=True):
        out = await extract_and_upload_scene_frames(
            tmp_path / "v.mp4", "vid-1", [],
        )
    assert out == []


@pytest.mark.asyncio
async def test_orchestrator_skips_scenes_with_invalid_bounds(tmp_path: Path) -> None:
    """A scene with end<=start is dropped silently (data corruption
    from some ingest source). Remaining scenes still extracted."""
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"fake")

    extract_mock = MagicMock(return_value=[])
    with patch("getviews_pipeline.r2.r2_configured", return_value=True), \
         patch("getviews_pipeline.r2.extract_scene_frames", extract_mock):
        await extract_and_upload_scene_frames(
            vid, "vid-1",
            [
                {"start": 0.0, "end": 2.0},  # valid
                {"start": 3.0, "end": 2.0},  # inverted — skip
                {"start": 2.0, "end": 2.0},  # zero-length — skip
                {"start": 4.0, "end": 6.0},  # valid
            ],
        )

    # extract called with 2 midpoints (indices 0 and 3)
    assert extract_mock.called
    midpoints_arg = extract_mock.call_args.args[2]
    assert [i for i, _ in midpoints_arg] == [0, 3]


@pytest.mark.asyncio
async def test_orchestrator_cleans_up_tmp_files_on_exception(tmp_path: Path) -> None:
    """If upload raises, /tmp frames still get cleaned — prevents
    disk fill on repeat ingest failures."""
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"fake")

    # Create real tmp files so we can assert they get unlinked
    tmp_frames: list[tuple[int, Path]] = []
    for i in range(2):
        p = tmp_path / f"scene_{i}.jpg"
        p.write_bytes(b"jpg")
        tmp_frames.append((i, p))

    with patch("getviews_pipeline.r2.r2_configured", return_value=True), \
         patch("getviews_pipeline.r2.extract_scene_frames", return_value=tmp_frames), \
         patch(
             "getviews_pipeline.r2.upload_scene_frames",
             side_effect=RuntimeError("boto3 went down"),
         ):
        out = await extract_and_upload_scene_frames(
            vid, "vid-1", [{"start": 0, "end": 2}, {"start": 3, "end": 5}],
        )

    assert out == []
    # Files should be removed
    for _, p in tmp_frames:
        assert not p.exists(), f"tmp file {p} was not cleaned up"
