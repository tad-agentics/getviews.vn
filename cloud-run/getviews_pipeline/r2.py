"""Cloudflare R2 frame extraction and upload.

Flow:
  1. extract_frames(video_path, video_id) → runs ffmpeg, writes PNGs to /tmp
  2. upload_frames(video_id, frame_paths) → uploads each PNG to R2, returns public URLs
  3. extract_and_upload(video_path, video_id) → combines both, cleans up /tmp files

Usage in corpus_ingest.py:
    from getviews_pipeline.r2 import extract_and_upload, r2_configured
    if r2_configured():
        frame_urls = await extract_and_upload(video_path, video_id)

When R2 credentials are missing or ffmpeg is unavailable, functions degrade
gracefully — they log a warning and return [] so corpus ingest continues.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from getviews_pipeline.config import (
    FRAME_TIMESTAMPS_SEC,
    R2_ACCESS_KEY_ID,
    R2_ACCOUNT_ID,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    R2_SECRET_ACCESS_KEY,
    R2_VIDEO_PUBLIC_URL,
)

logger = logging.getLogger(__name__)

# R2 uses S3-compatible API at this endpoint pattern
_R2_ENDPOINT = "https://{account_id}.r2.cloudflarestorage.com"

# MIME type for extracted frames
_FRAME_CONTENT_TYPE = "image/png"
_FRAME_EXT = ".png"

# Max bytes we'll upload per frame (guard against runaway ffmpeg output)
_MAX_FRAME_BYTES = 5 * 1024 * 1024  # 5 MB

# Video upload settings
_VIDEO_CONTENT_TYPE = "video/mp4"
# Guard: skip upload if clip is larger than 60 MB (should be well under for 30s 720p)
_MAX_VIDEO_BYTES = 60 * 1024 * 1024  # 60 MB


def r2_configured() -> bool:
    """Returns True when all required R2 env vars are set."""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_PUBLIC_URL)


def _get_r2_client() -> Any:
    """Create a boto3 S3 client pointed at Cloudflare R2."""
    endpoint = _R2_ENDPOINT.format(account_id=R2_ACCOUNT_ID)
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_frames(video_path: Path, video_id: str) -> list[Path]:
    """Extract PNG frames from video_path at FRAME_TIMESTAMPS_SEC using ffmpeg.

    Runs synchronously (call via run_in_executor for async contexts).
    Returns list of frame paths on disk (caller is responsible for cleanup).
    Returns [] if ffmpeg is unavailable or extraction fails.
    """
    if not _ffmpeg_available():
        logger.warning("[r2] ffmpeg not found — frame extraction skipped for %s", video_id)
        return []

    if not video_path.exists():
        logger.warning("[r2] video_path %s does not exist", video_path)
        return []

    frame_paths: list[Path] = []
    run_id = uuid.uuid4().hex[:8]

    for i, ts in enumerate(FRAME_TIMESTAMPS_SEC):
        out_path = Path("/tmp") / f"frame_{video_id}_{run_id}_{i}{_FRAME_EXT}"
        cmd = [
            "ffmpeg",
            "-y",                    # overwrite without prompt
            "-ss", str(ts),          # seek to timestamp
            "-i", str(video_path),   # input file
            "-vframes", "1",         # extract exactly one frame
            "-vf", "scale=720:-2",   # resize width=720, keep aspect ratio
            "-q:v", "3",             # PNG compression quality (1=best, 31=worst)
            str(out_path),
        ]
        try:
            import subprocess

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(
                    "[r2] ffmpeg failed for %s ts=%.1fs: %s",
                    video_id,
                    ts,
                    result.stderr.decode(errors="replace")[:200],
                )
                continue
            if out_path.exists() and out_path.stat().st_size > 0:
                if out_path.stat().st_size > _MAX_FRAME_BYTES:
                    logger.warning(
                        "[r2] frame %s at ts=%.1fs is %.1fMB — skipping (too large)",
                        video_id,
                        ts,
                        out_path.stat().st_size / 1024 / 1024,
                    )
                    out_path.unlink(missing_ok=True)
                    continue
                frame_paths.append(out_path)
                logger.debug(
                    "[r2] extracted frame %d/%d for %s at ts=%.1fs (%d bytes)",
                    i + 1,
                    len(FRAME_TIMESTAMPS_SEC),
                    video_id,
                    ts,
                    out_path.stat().st_size,
                )
            else:
                logger.warning("[r2] ffmpeg produced empty frame for %s ts=%.1fs", video_id, ts)
        except Exception as exc:
            logger.warning("[r2] ffmpeg error for %s ts=%.1fs: %s", video_id, ts, exc)

    logger.info("[r2] extracted %d/%d frames for %s", len(frame_paths), len(FRAME_TIMESTAMPS_SEC), video_id)
    return frame_paths


def upload_frames(video_id: str, frame_paths: list[Path]) -> list[str]:
    """Upload frame PNGs to R2 and return their public URLs.

    Key pattern: frames/{video_id}/{i}.png
    Runs synchronously (call via run_in_executor for async contexts).
    Returns [] if upload fails entirely; partial successes are included.
    """
    if not r2_configured():
        logger.warning("[r2] R2 not configured — skipping upload for %s", video_id)
        return []

    if not frame_paths:
        return []

    try:
        client = _get_r2_client()
    except Exception as exc:
        logger.error("[r2] failed to create R2 client: %s", exc)
        return []

    public_urls: list[str] = []

    for i, path in enumerate(frame_paths):
        if not path.exists():
            logger.warning("[r2] frame path %s does not exist, skipping", path)
            continue

        key = f"frames/{video_id}/{i}{_FRAME_EXT}"
        try:
            with path.open("rb") as fh:
                client.put_object(
                    Bucket=R2_BUCKET_NAME,
                    Key=key,
                    Body=fh,
                    ContentType=_FRAME_CONTENT_TYPE,
                    CacheControl="public, max-age=31536000, immutable",
                )
            url = f"{R2_PUBLIC_URL}/{key}"
            public_urls.append(url)
            logger.debug("[r2] uploaded %s → %s", path.name, url)
        except (BotoCoreError, ClientError) as exc:
            logger.error("[r2] R2 upload failed for %s key=%s: %s", video_id, key, exc)
        except Exception as exc:
            logger.error("[r2] unexpected error uploading %s: %s", key, exc)

    logger.info(
        "[r2] uploaded %d/%d frames for %s",
        len(public_urls),
        len(frame_paths),
        video_id,
    )
    return public_urls


def _cleanup_frames(frame_paths: list[Path]) -> None:
    for p in frame_paths:
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


async def extract_and_upload(video_path: Path, video_id: str) -> list[str]:
    """Extract frames + upload to R2. Returns public URLs. Always cleans up /tmp files.

    Designed to be awaited inside corpus_ingest after download_video() succeeds.
    Never raises — returns [] on any failure so corpus ingest continues.
    """
    if not r2_configured():
        return []

    loop = asyncio.get_event_loop()
    frame_paths: list[Path] = []

    try:
        frame_paths = await loop.run_in_executor(None, extract_frames, video_path, video_id)
        if not frame_paths:
            return []

        urls = await loop.run_in_executor(None, upload_frames, video_id, frame_paths)
        return urls
    except Exception as exc:
        logger.error("[r2] extract_and_upload failed for %s: %s", video_id, exc)
        return []
    finally:
        _cleanup_frames(frame_paths)


async def download_and_extract_frames(
    video_urls: list[str],
    video_id: str,
) -> list[str]:
    """Download a short clip (first 5s) → extract frames → upload to R2.

    Used by corpus_ingest to avoid modifying analysis_core internals.
    The short clip download is much cheaper than a full re-download:
    ffmpeg's -t flag stops reading after 5 seconds.

    Never raises. Returns [] on any failure.
    """
    if not r2_configured():
        return []

    if not video_urls:
        return []

    if not _ffmpeg_available():
        logger.warning("[r2] ffmpeg not available — skipping frame extraction for %s", video_id)
        return []

    import subprocess

    loop = asyncio.get_event_loop()
    clip_path = Path("/tmp") / f"clip_{video_id}_{uuid.uuid4().hex[:8]}.mp4"

    def _download_clip() -> bool:
        """Use ffmpeg to download only the first FRAME_TIMESTAMPS_SEC[-1]+1 seconds."""
        max_ts = max(FRAME_TIMESTAMPS_SEC, default=3.0) + 1.5
        for url in video_urls:
            cmd = [
                "ffmpeg",
                "-y",
                "-t", str(max_ts),      # stop reading after max_ts seconds
                "-i", url,              # HTTP input — ffmpeg streams directly
                "-c", "copy",           # no re-encode, just copy packets
                str(clip_path),
            ]
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=60,
                )
                if res.returncode == 0 and clip_path.exists() and clip_path.stat().st_size > 0:
                    logger.debug(
                        "[r2] downloaded clip for %s: %.1fKB",
                        video_id,
                        clip_path.stat().st_size / 1024,
                    )
                    return True
                logger.debug(
                    "[r2] clip download failed for %s (url=%s...): %s",
                    video_id,
                    url[:60],
                    res.stderr.decode(errors="replace")[:200],
                )
            except Exception as exc:
                logger.debug("[r2] clip download error for %s: %s", video_id, exc)
        return False

    try:
        ok = await loop.run_in_executor(None, _download_clip)
        if not ok:
            logger.warning("[r2] clip download failed for all URLs of %s", video_id)
            return []
        return await extract_and_upload(clip_path, video_id)
    finally:
        clip_path.unlink(missing_ok=True)


def upload_video(video_id: str, clip_path: Path) -> str | None:
    """Upload a 720p/30s .mp4 clip to R2 at videos/{video_id}.mp4.

    Returns the permanent public URL (R2_VIDEO_PUBLIC_URL/videos/{video_id}.mp4)
    or None on any failure.

    Key pattern: videos/{video_id}.mp4
    CacheControl: immutable — the clip content is stable once uploaded.
    Runs synchronously (call via run_in_executor for async contexts).
    """
    if not r2_configured():
        logger.warning("[r2] R2 not configured — skipping video upload for %s", video_id)
        return None

    public_base = R2_VIDEO_PUBLIC_URL or R2_PUBLIC_URL
    if not public_base:
        logger.warning("[r2] No public URL configured for video upload of %s", video_id)
        return None

    if not clip_path.exists():
        logger.warning("[r2] clip_path %s does not exist — skipping upload", clip_path)
        return None

    size = clip_path.stat().st_size
    if size == 0:
        logger.warning("[r2] clip_path %s is empty — skipping upload", clip_path)
        return None

    if size > _MAX_VIDEO_BYTES:
        logger.warning(
            "[r2] clip %s is %.1fMB — exceeds %dMB limit, skipping upload",
            video_id,
            size / 1024 / 1024,
            _MAX_VIDEO_BYTES // 1024 // 1024,
        )
        return None

    key = f"videos/{video_id}.mp4"
    try:
        client = _get_r2_client()
        with clip_path.open("rb") as fh:
            client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=key,
                Body=fh,
                ContentType=_VIDEO_CONTENT_TYPE,
                CacheControl="public, max-age=31536000, immutable",
            )
        url = f"{public_base.rstrip('/')}/{key}"
        logger.info("[r2] uploaded video %s → %s (%.1fKB)", video_id, url, size / 1024)
        return url
    except (BotoCoreError, ClientError) as exc:
        logger.error("[r2] R2 video upload failed for %s: %s", video_id, exc)
        return None
    except Exception as exc:
        logger.error("[r2] unexpected error uploading video %s: %s", video_id, exc)
        return None


async def download_and_upload_video(
    video_urls: list[str],
    video_id: str,
) -> str | None:
    """Download a 720p/30s clip → upload to R2 → return permanent public URL.

    Used by corpus_ingest to replace the ephemeral ED CDN video_url with a
    permanent R2 URL suitable for Explore inline playback (zero egress cost).

    The clip is downloaded with ffmpeg -t 32 (32 seconds = 30s content + buffer)
    at 720p equivalent bitrate via stream copy — no re-encode, no quality loss.

    Returns the permanent R2 URL on success, or None on any failure (non-fatal).
    Cleans up /tmp regardless.
    """
    if not r2_configured():
        return None

    if not video_urls:
        return None

    if not _ffmpeg_available():
        logger.warning("[r2] ffmpeg not available — skipping video upload for %s", video_id)
        return None

    import subprocess

    loop = asyncio.get_event_loop()
    clip_path = Path("/tmp") / f"video_{video_id}_{uuid.uuid4().hex[:8]}.mp4"

    def _download_30s_clip() -> bool:
        """Download first 30s of the video via ffmpeg stream copy."""
        for url in video_urls:
            cmd = [
                "ffmpeg",
                "-y",
                "-t", "32",          # 30s content + 2s buffer
                "-i", url,           # HTTP input — ffmpeg streams directly
                "-c", "copy",        # no re-encode — preserve original quality
                "-movflags", "+faststart",  # moov atom at front for streaming
                str(clip_path),
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, timeout=90)
                if res.returncode == 0 and clip_path.exists() and clip_path.stat().st_size > 0:
                    logger.debug(
                        "[r2] downloaded 30s clip for %s: %.1fMB",
                        video_id,
                        clip_path.stat().st_size / 1024 / 1024,
                    )
                    return True
                logger.debug(
                    "[r2] 30s clip download failed for %s (url=%s...): %s",
                    video_id,
                    url[:60],
                    res.stderr.decode(errors="replace")[:200],
                )
            except Exception as exc:
                logger.debug("[r2] 30s clip download error for %s: %s", video_id, exc)
        return False

    try:
        ok = await loop.run_in_executor(None, _download_30s_clip)
        if not ok:
            logger.warning("[r2] 30s clip download failed for all URLs of %s", video_id)
            return None
        return await loop.run_in_executor(None, upload_video, video_id, clip_path)
    except Exception as exc:
        logger.error("[r2] download_and_upload_video failed for %s: %s", video_id, exc)
        return None
    finally:
        clip_path.unlink(missing_ok=True)
