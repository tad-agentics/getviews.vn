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
import subprocess
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from getviews_pipeline.config import (
    FFMPEG_FRAME_FALLBACK_SCALE_WIDTH,
    FFMPEG_FRAME_TIMEOUT_SEC,
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

# User-facing card thumbnails — 360w WebP (frames/ stay 720 PNG for Gemini).
_THUMB_EXT = ".webp"
_THUMB_CONTENT_TYPE = "image/webp"
_THUMB_SCALE_WIDTH = 360
_THUMB_WEBP_QUALITY = 80
_THUMBNAIL_EXTS = (_THUMB_EXT, _FRAME_EXT, ".jpg")
_MAX_THUMB_OUTPUT_BYTES = 512 * 1024  # 512 KB guard after transcode

# 2026-05-10 — Wave 2.5 Phase A PR #3: per-scene frames use JPG (smaller,
# adequate quality for thumbnails at ~720px). Key pattern
# ``video_shots/{video_id}/{scene_index}.jpg`` matches the matcher's
# expected frame_url column shape on video_shots.
_SCENE_FRAME_CONTENT_TYPE = "image/jpeg"
_SCENE_FRAME_EXT = ".jpg"
# Ffmpeg refuses to seek to 0.0 on some containers; clamp to this
# floor so "first scene starts at 0" still returns a frame.
_SCENE_FRAME_MIN_TS = 0.1

# Max bytes we'll upload per frame (guard against runaway ffmpeg output)
_MAX_FRAME_BYTES = 5 * 1024 * 1024  # 5 MB

# Video upload settings
_VIDEO_CONTENT_TYPE = "video/mp4"
# Guard: skip upload if clip is larger than 60 MB (should be well under for 30s 720p)
_MAX_VIDEO_BYTES = 60 * 1024 * 1024  # 60 MB


def r2_configured() -> bool:
    """Returns True when all required R2 env vars are set."""
    return bool(R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_PUBLIC_URL)


def r2_object_exists(key: str) -> bool:
    """Return True when ``key`` is present in the configured R2 bucket."""
    if not r2_configured() or not R2_BUCKET_NAME or not key:
        return False
    try:
        client = _get_r2_client()
        client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        logger.warning("[r2] head_object failed for %s: %s", key, exc)
        return False
    except (BotoCoreError, Exception) as exc:
        logger.warning("[r2] head_object error for %s: %s", key, exc)
        return False


def r2_public_thumbnail_exists(video_id: str) -> bool:
    """True when ``thumbnails/{video_id}.webp`` exists (optimized user-facing thumb)."""
    if not video_id:
        return False
    return r2_object_exists(f"thumbnails/{video_id}{_THUMB_EXT}")


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


def _input_seek_sec(ts: float) -> float:
    """Timestamp for ``-ss`` before ``-i`` (fast input seek). Avoid 0.0 on
    some containers; align with scene midpoint floor.
    """
    return max(_SCENE_FRAME_MIN_TS, float(ts))


def _ffmpeg_extract_still(
    video_path: Path,
    out_path: Path,
    seek_sec: float,
    *,
    scale_w: int,
    timeout_sec: float,
    png_q: int,
    jpg_q: int,
) -> bool:
    """Run ffmpeg: input seek, strip audio/subs, one video frame, scale.

    Returns True if a non-empty file under ``_MAX_FRAME_BYTES`` was written.
    """
    out_path.unlink(missing_ok=True)
    is_jpg = out_path.suffix.lower() in (".jpg", ".jpeg")
    cmd: list[str] = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-nostdin",
        "-ss",
        str(seek_sec),
        "-i",
        str(video_path),
        "-an",
        "-sn",
        "-dn",
        "-vframes",
        "1",
        "-vf",
        f"scale={scale_w}:-2",
    ]
    if is_jpg:
        cmd.extend(["-q:v", str(jpg_q)])
    else:
        cmd.extend(["-q:v", str(png_q)])
    cmd.append(str(out_path))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False
    if result.returncode != 0:
        return False
    if not out_path.exists() or out_path.stat().st_size == 0:
        return False
    if out_path.stat().st_size > _MAX_FRAME_BYTES:
        out_path.unlink(missing_ok=True)
        return False
    return True


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
        seek = _input_seek_sec(ts)
        ok = False
        for scale_w, png_q, jpg_q in (
            (720, 3, 4),
            (FFMPEG_FRAME_FALLBACK_SCALE_WIDTH, 5, 7),
        ):
            if _ffmpeg_extract_still(
                video_path,
                out_path,
                seek,
                scale_w=scale_w,
                timeout_sec=float(FFMPEG_FRAME_TIMEOUT_SEC),
                png_q=png_q,
                jpg_q=jpg_q,
            ):
                ok = True
                break
        if not ok:
            logger.warning(
                "[r2] ffmpeg failed for %s ts=%.1fs after %ds timeout + fallback scale",
                video_id,
                ts,
                FFMPEG_FRAME_TIMEOUT_SEC,
            )
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

    logger.info(
        "[r2] extracted %d/%d frames for %s",
        len(frame_paths),
        len(FRAME_TIMESTAMPS_SEC),
        video_id,
    )
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


def _delete_stale_thumbnail_exts(video_id: str, *, keep_ext: str) -> None:
    """Delete legacy thumbnail keys for ``video_id`` except ``keep_ext``.

    Enforces at most one extension per video_id under ``thumbnails/``.
    Non-fatal — failures log at debug/warning and return.
    """
    for ext in _THUMBNAIL_EXTS:
        if ext == keep_ext:
            continue
        other_key = f"thumbnails/{video_id}{ext}"
        try:
            client = _get_r2_client()
            client.delete_object(Bucket=R2_BUCKET_NAME, Key=other_key)
            logger.debug("[r2] deleted stale thumbnail %s", other_key)
        except (BotoCoreError, ClientError) as exc:
            logger.debug("[r2] delete stale thumbnail %s: %s", other_key, exc)
        except Exception as exc:
            logger.warning("[r2] unexpected error deleting stale thumbnail %s: %s", other_key, exc)


def _ffmpeg_transcode_to_webp(
    src_path: Path,
    dst_path: Path,
    *,
    scale_w: int = _THUMB_SCALE_WIDTH,
    quality: int = _THUMB_WEBP_QUALITY,
) -> bool:
    """Scale still image to ``scale_w`` and write WebP. Returns True on success."""
    if not _ffmpeg_available():
        return False
    dst_path.unlink(missing_ok=True)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-nostdin",
        "-i",
        str(src_path),
        "-vf",
        f"scale={scale_w}:-2",
        "-frames:v",
        "1",
        "-c:v",
        "libwebp",
        "-quality",
        str(quality),
        str(dst_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30.0)
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False
    if result.returncode != 0:
        return False
    if not dst_path.exists() or dst_path.stat().st_size == 0:
        dst_path.unlink(missing_ok=True)
        return False
    if dst_path.stat().st_size > _MAX_THUMB_OUTPUT_BYTES:
        logger.warning(
            "[r2] webp thumbnail too large (%dKB) after transcode — rejecting",
            dst_path.stat().st_size // 1024,
        )
        dst_path.unlink(missing_ok=True)
        return False
    return True


def _download_r2_object_to_path(key: str, dest: Path) -> bool:
    """Download one R2 object to a local path. Returns True on success."""
    try:
        client = _get_r2_client()
        dest.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(R2_BUCKET_NAME, key, str(dest))
        return dest.exists() and dest.stat().st_size > 0
    except (BotoCoreError, ClientError) as exc:
        logger.debug("[r2] download %s failed: %s", key, exc)
        return False
    except Exception as exc:
        logger.warning("[r2] unexpected download error for %s: %s", key, exc)
        return False


def _put_thumbnail_webp(video_id: str, webp_bytes: bytes) -> str | None:
    """Upload optimized WebP bytes to ``thumbnails/{video_id}.webp``."""
    if not r2_configured() or not webp_bytes:
        return None
    key = f"thumbnails/{video_id}{_THUMB_EXT}"
    try:
        client = _get_r2_client()
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=webp_bytes,
            ContentType=_THUMB_CONTENT_TYPE,
            CacheControl="public, max-age=31536000, immutable",
        )
        url = f"{R2_PUBLIC_URL.rstrip('/')}/{key}"
        logger.info(
            "[r2] uploaded webp thumbnail %s → %s (%dKB)",
            video_id,
            url,
            len(webp_bytes) // 1024,
        )
        _delete_stale_thumbnail_exts(video_id, keep_ext=_THUMB_EXT)
        return url
    except (BotoCoreError, ClientError) as exc:
        logger.error("[r2] webp thumbnail upload failed for %s: %s", video_id, exc)
        return None
    except Exception as exc:
        logger.error("[r2] unexpected error uploading webp thumbnail %s: %s", video_id, exc)
        return None


def _transcode_local_image_to_webp_thumbnail(video_id: str, src_path: Path) -> str | None:
    """Transcode a local still → 360w WebP on R2. Cleans up temp output."""
    run_id = uuid.uuid4().hex[:8]
    out_path = Path("/tmp") / f"thumb_webp_{video_id}_{run_id}{_THUMB_EXT}"
    try:
        if not _ffmpeg_transcode_to_webp(src_path, out_path):
            return None
        return _put_thumbnail_webp(video_id, out_path.read_bytes())
    finally:
        out_path.unlink(missing_ok=True)


def copy_first_frame_to_thumbnail(video_id: str) -> str | None:
    """Derive a 360w WebP user-facing thumbnail from frame[0] (or legacy PNG).

    Analysis frames stay at ``frames/{video_id}/0.png`` (720px PNG for Gemini).
    User-facing cards read ``thumbnails/{video_id}.webp`` (~15–40 KB vs
    200–850 KB legacy PNG copies).

    Source order:
      1. ``frames/{video_id}/0.png`` (preferred — deterministic hook frame)
      2. ``thumbnails/{video_id}.png`` (legacy re-encode during backfill)

    Returns the permanent R2 public URL on success; ``None`` on skip/failure.
    Non-fatal — corpus ingest continues with platform CDN URL as fallback.
    """
    if not r2_configured():
        return None

    src_key = f"frames/{video_id}/0{_FRAME_EXT}"
    if not r2_object_exists(src_key):
        legacy_key = f"thumbnails/{video_id}{_FRAME_EXT}"
        if r2_object_exists(legacy_key):
            src_key = legacy_key
        else:
            return None

    run_id = uuid.uuid4().hex[:8]
    tmp_src = Path("/tmp") / f"thumb_src_{video_id}_{run_id}{_FRAME_EXT}"
    try:
        if not _download_r2_object_to_path(src_key, tmp_src):
            return None
        return _transcode_local_image_to_webp_thumbnail(video_id, tmp_src)
    finally:
        tmp_src.unlink(missing_ok=True)


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


# ── Thumbnail upload ──────────────────────────────────────────────────────────

# Max bytes accepted for a thumbnail image (guard against runaway CDN responses)
_MAX_THUMB_BYTES = 2 * 1024 * 1024  # 2 MB

def upload_thumbnail_bytes(video_id: str, image_bytes: bytes, content_type: str = "image/jpeg") -> str | None:
    """Transcode raw thumbnail bytes → 360w WebP at ``thumbnails/{video_id}.webp``.

    Returns the permanent public URL on success, None on failure.
    Runs synchronously — call via run_in_executor for async contexts.
    """
    if not r2_configured():
        return None
    if not image_bytes:
        return None
    if len(image_bytes) > _MAX_THUMB_BYTES:
        logger.warning("[r2] thumbnail source too large (%dKB) for %s", len(image_bytes) // 1024, video_id)
        return None

    run_id = uuid.uuid4().hex[:8]
    src_ext = ".jpg" if "jpeg" in content_type or "jpg" in content_type else ".png"
    tmp_src = Path("/tmp") / f"thumb_in_{video_id}_{run_id}{src_ext}"
    try:
        tmp_src.write_bytes(image_bytes)
        return _transcode_local_image_to_webp_thumbnail(video_id, tmp_src)
    except Exception as exc:
        logger.error("[r2] thumbnail transcode failed for %s: %s", video_id, exc)
        return None
    finally:
        tmp_src.unlink(missing_ok=True)


async def download_and_upload_thumbnail(thumbnail_url: str, video_id: str) -> str | None:
    """Download a TikTok CDN thumbnail URL → upload to R2 → return permanent public URL.

    TikTok CDN thumbnails (tiktokcdn-eu.com) are served via signed URLs that
    expire within hours. Uploading to R2 on ingest gives a permanent URL with
    zero recurring cost (R2 egress is free; storage is ~$0.015/GB).

    Flow:
      1. HTTP GET the thumbnail URL through the residential-proxy CDN client
         with TikTok ``Referer`` / browser ``User-Agent`` (TikTok's CDN replies
         ``403 host_not_allowed`` to bare datacenter IPs and wrong referers)
      2. Validate content-type is image/* and size < _MAX_THUMB_BYTES
      3. PUT bytes to R2 at thumbnails/{video_id}.webp (360w transcode)
      4. Return the permanent R2 public URL, or None on any failure (non-fatal)

    Skipped gracefully when:
      - R2 is not configured (r2_configured() = False)
      - thumbnail_url is empty or None
      - Download fails or returns a non-image content type
    """
    if not r2_configured():
        return None
    if not thumbnail_url:
        return None

    # Lazy import avoids a circular dep (ensemble imports r2 transitively).
    from getviews_pipeline.config import CDN_HEADERS
    from getviews_pipeline.ensemble import get_cdn_client

    loop = asyncio.get_event_loop()

    try:
        client = await get_cdn_client()
        resp = await client.get(
            thumbnail_url,
            headers=CDN_HEADERS,
            follow_redirects=True,
            timeout=15.0,
        )
    except Exception as exc:
        logger.debug("[r2] thumbnail download error for %s: %s", video_id, exc)
        return None

    if resp.status_code != 200:
        logger.debug(
            "[r2] thumbnail fetch returned %d for %s (deny=%s)",
            resp.status_code, video_id, resp.headers.get("x-deny-reason", "-"),
        )
        return None
    content_type = resp.headers.get("content-type", "image/jpeg")
    if not content_type.startswith("image/"):
        logger.debug("[r2] thumbnail content-type unexpected (%s) for %s", content_type, video_id)
        return None
    image_bytes = resp.content
    if len(image_bytes) > _MAX_THUMB_BYTES:
        logger.warning("[r2] thumbnail too large (%dKB) for %s", len(image_bytes) // 1024, video_id)
        return None

    try:
        return await loop.run_in_executor(
            None, upload_thumbnail_bytes, video_id, image_bytes, content_type,
        )
    except Exception as exc:
        logger.error("[r2] download_and_upload_thumbnail failed for %s: %s", video_id, exc)
        return None


# ── Per-scene frame extraction (Wave 2.5 Phase A PR #3) ────────────────
#
# Distinct from extract_frames() / upload_frames() above, which target the
# fixed FRAME_TIMESTAMPS_SEC (hook-window coverage for diagnosis). These
# scene-frame helpers extract ONE frame per video_corpus.scenes[] entry at
# its midpoint, for the "reference videos per script shot" matcher.
#
# Key pattern: video_shots/{video_id}/{scene_index}.jpg
# Format: JPG (smaller files, adequate for thumbnails). Stored on the same
# R2 bucket as the hook frames, in a separate folder namespace.


def _scene_midpoint(start: float, end: float) -> float:
    """Clamp midpoint to the ffmpeg-seek-safe floor."""
    mid = (float(start) + float(end)) / 2.0
    return max(_SCENE_FRAME_MIN_TS, mid)


def extract_scene_frames(
    video_path: Path,
    video_id: str,
    scene_midpoints: list[tuple[int, float]],
) -> list[tuple[int, Path]]:
    """Extract one JPG frame per (scene_index, timestamp) pair.

    Runs synchronously — call via ``run_in_executor`` from async callers.
    Returns ``[(scene_index, path)]`` for successful extractions only;
    length may be shorter than input when individual ffmpeg runs fail.
    Never raises — returns ``[]`` if ffmpeg is unavailable or video_path
    is missing.
    """
    if not _ffmpeg_available():
        logger.warning(
            "[r2] ffmpeg not found — scene frame extraction skipped for %s", video_id,
        )
        return []
    if not video_path.exists():
        logger.warning("[r2] video_path %s does not exist", video_path)
        return []

    run_id = uuid.uuid4().hex[:8]
    results: list[tuple[int, Path]] = []

    for scene_index, ts in scene_midpoints:
        safe_ts = _input_seek_sec(float(ts))
        out_path = Path("/tmp") / (
            f"scene_{video_id}_{run_id}_{scene_index}{_SCENE_FRAME_EXT}"
        )
        ok = False
        for scale_w, jpg_q in (
            (720, 4),
            (FFMPEG_FRAME_FALLBACK_SCALE_WIDTH, 7),
        ):
            if _ffmpeg_extract_still(
                video_path,
                out_path,
                safe_ts,
                scale_w=scale_w,
                timeout_sec=float(FFMPEG_FRAME_TIMEOUT_SEC),
                png_q=3,
                jpg_q=jpg_q,
            ):
                ok = True
                break
        if not ok:
            logger.warning(
                "[r2] scene extraction failed %s scene=%d ts=%.2fs (timeout %ds + fallback)",
                video_id,
                scene_index,
                safe_ts,
                FFMPEG_FRAME_TIMEOUT_SEC,
            )
            continue
        results.append((scene_index, out_path))

    logger.info(
        "[r2] extracted %d/%d scene frames for %s",
        len(results), len(scene_midpoints), video_id,
    )
    return results


def upload_scene_frames(
    video_id: str,
    scene_frames: list[tuple[int, Path]],
) -> list[tuple[int, str]]:
    """Upload scene JPG frames to R2.

    Key pattern: ``video_shots/{video_id}/{scene_index}.jpg``
    Returns ``[(scene_index, public_url)]``. Partial successes included;
    returns ``[]`` on full failure. Never raises.
    """
    if not r2_configured():
        logger.warning(
            "[r2] R2 not configured — scene frame upload skipped for %s", video_id,
        )
        return []
    if not scene_frames:
        return []

    try:
        client = _get_r2_client()
    except Exception as exc:
        logger.error("[r2] failed to create R2 client: %s", exc)
        return []

    uploaded: list[tuple[int, str]] = []
    for scene_index, path in scene_frames:
        if not path.exists():
            continue
        key = f"video_shots/{video_id}/{scene_index}{_SCENE_FRAME_EXT}"
        try:
            with path.open("rb") as fh:
                client.put_object(
                    Bucket=R2_BUCKET_NAME,
                    Key=key,
                    Body=fh,
                    ContentType=_SCENE_FRAME_CONTENT_TYPE,
                    CacheControl="public, max-age=31536000, immutable",
                )
            url = f"{R2_PUBLIC_URL}/{key}"
            uploaded.append((scene_index, url))
        except (BotoCoreError, ClientError) as exc:
            logger.error(
                "[r2] scene upload failed %s scene=%d: %s",
                video_id, scene_index, exc,
            )
        except Exception as exc:
            logger.error(
                "[r2] unexpected error uploading scene %s:%d: %s",
                video_id, scene_index, exc,
            )

    logger.info(
        "[r2] uploaded %d/%d scene frames for %s",
        len(uploaded), len(scene_frames), video_id,
    )
    return uploaded


async def extract_and_upload_scene_frames(
    video_path: Path,
    video_id: str,
    scenes: list[dict[str, Any]],
) -> list[tuple[int, str]]:
    """Extract + upload one frame per scene, at its midpoint.

    ``scenes`` is a list of dicts (or pydantic dumps) with ``start`` +
    ``end`` keys. ``scene_index`` is derived from list position. Returns
    ``[(scene_index, url)]``. Always cleans up /tmp files. Never raises.
    Designed for ingest call sites: on any failure, returns ``[]`` so
    the broader ingest continues.
    """
    if not r2_configured() or not scenes:
        return []

    midpoints: list[tuple[int, float]] = []
    for i, sc in enumerate(scenes):
        try:
            start = float(sc.get("start", 0.0) or 0.0)
            end = float(sc.get("end", 0.0) or 0.0)
            if end <= start:
                continue
            midpoints.append((i, _scene_midpoint(start, end)))
        except (TypeError, ValueError):
            continue

    if not midpoints:
        return []

    loop = asyncio.get_event_loop()
    frame_pairs: list[tuple[int, Path]] = []
    try:
        frame_pairs = await loop.run_in_executor(
            None, extract_scene_frames, video_path, video_id, midpoints,
        )
        if not frame_pairs:
            return []
        uploaded = await loop.run_in_executor(
            None, upload_scene_frames, video_id, frame_pairs,
        )
        return uploaded
    except Exception as exc:
        logger.error(
            "[r2] extract_and_upload_scene_frames failed for %s: %s", video_id, exc,
        )
        return []
    finally:
        _cleanup_frames([p for _, p in frame_pairs])
