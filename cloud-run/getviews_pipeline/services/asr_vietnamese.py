"""HI-14 — GCP Speech-to-Text (vi-VN) supplemental transcript for video extraction.

Runs before ``gemini.analyze_video``, caches by TikTok ``video_id`` in
``vietnamese_asr_cache``, and returns a short Vietnamese text block for the
user turn. Failures are logged; callers treat an empty prefix as graceful skip.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from google.cloud import speech_v1 as speech

from getviews_pipeline.config import GCP_STT_VI_ENABLED, GCP_STT_VI_PRICE_PER_MIN_USD
from getviews_pipeline.prompts import format_vietnamese_asr_supplement_for_video_extraction_vi
from getviews_pipeline.supabase_client import get_service_client

logger = logging.getLogger(__name__)


def _ffprobe_duration_sec(media_path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = (out.stdout or "").strip()
    if not raw or raw == "N/A":
        return 0.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


def _extract_wav_16k_mono(video_path: Path) -> Path:
    """Write a linear PCM WAV (16 kHz mono) to a temp file; caller must unlink."""
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    # Close fd — ffmpeg overwrites the path
    import os

    os.close(fd)
    out_path = Path(tmp)
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            "-y",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return out_path


def _row_to_transcript_payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("transcript")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _fetch_cache(video_id: str) -> dict[str, Any] | None:
    try:
        res = (
            get_service_client()
            .table("vietnamese_asr_cache")
            .select("transcript,stt_cost_usd,audio_duration_sec")
            .eq("video_id", video_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("[hi14] asr cache read failed video_id=%s: %s", video_id, exc)
        return None


def _upsert_cache(
    *,
    video_id: str,
    transcript: dict[str, Any],
    stt_cost_usd: float,
    audio_duration_sec: float | None,
) -> None:
    try:
        payload = {
            "video_id": video_id,
            "transcript": transcript,
            "stt_cost_usd": round(stt_cost_usd, 6),
            "audio_duration_sec": audio_duration_sec,
        }
        get_service_client().table("vietnamese_asr_cache").upsert(payload).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[hi14] asr cache write failed video_id=%s: %s", video_id, exc)


def _stt_cost_for_duration(duration_sec: float) -> float:
    if duration_sec <= 0:
        return 0.0
    mins = duration_sec / 60.0
    return round(mins * float(GCP_STT_VI_PRICE_PER_MIN_USD), 6)


def _protobuf_duration_sec(d: Any) -> float | None:
    if d is None:
        return None
    sec = int(getattr(d, "seconds", 0) or 0)
    nanos = int(getattr(d, "nanos", 0) or 0)
    return sec + nanos / 1_000_000_000.0


def _parse_recognition_results(response: Any) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    results = getattr(response, "results", None) or []
    for result in results:
        alts = getattr(result, "alternatives", None) or []
        if not alts:
            continue
        alt = alts[0]
        text = str(getattr(alt, "transcript", "") or "").strip()
        if not text:
            continue
        start_sec: float | None = None
        end_sec: float | None = None
        words = getattr(alt, "words", None) or []
        if words:
            try:
                start_sec = _protobuf_duration_sec(getattr(words[0], "start_time", None))
                end_sec = _protobuf_duration_sec(getattr(words[-1], "end_time", None))
            except Exception:  # noqa: BLE001
                start_sec, end_sec = None, None
        segments.append(
            {"start_sec": start_sec, "end_sec": end_sec, "text": text},
        )
    return segments


def _transcribe_wav_path(wav_path: Path, *, duration_sec: float) -> list[dict[str, Any]]:
    client = speech.SpeechClient()
    audio_bytes = wav_path.read_bytes()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16_000,
        language_code="vi-VN",
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
        model="default",
    )
    # Sync API caps audio length; long-form uses LRO.
    if duration_sec <= 55.0:
        response = client.recognize(config=config, audio=audio)
    else:
        op = client.long_running_recognize(config=config, audio=audio)
        response = op.result(timeout=600)
    return _parse_recognition_results(response)


def sync_prepare_vietnamese_asr_supplement(
    video_path: Path,
    video_id: str,
) -> tuple[str, float | None]:
    """Return ``(user_turn_prefix, gcp_stt_cost_usd)`` for ``analyze_video``.

    - Prefix is empty when STT is disabled, ``video_id`` is blank, audio
      extract fails, STT fails, or no speech is detected.
    - ``gcp_stt_cost_usd`` is ``None`` on cache hit, failures, or when no
      charge applies; otherwise the USD estimate for this STT call (not cached).
    """
    if not GCP_STT_VI_ENABLED:
        return "", None
    vid = str(video_id or "").strip()
    if not vid:
        return "", None
    path = video_path.resolve()
    if not path.is_file():
        return "", None

    cached = _fetch_cache(vid)
    if cached:
        payload = _row_to_transcript_payload(cached)
        text = format_vietnamese_asr_supplement_for_video_extraction_vi(
            list(payload.get("segments") or []),
        )
        return (text, None)

    wav_path: Path | None = None
    try:
        try:
            wav_path = _extract_wav_16k_mono(path)
        except subprocess.CalledProcessError as exc:
            logger.warning("[hi14] ffmpeg audio extract failed video_id=%s: %s", vid, exc)
            return "", None

        duration_sec = _ffprobe_duration_sec(wav_path)
        try:
            segments = _transcribe_wav_path(wav_path, duration_sec=duration_sec)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[hi14] speech recognize failed video_id=%s: %s", vid, exc)
            return "", None

        if not segments:
            return "", None

        stt_cost = _stt_cost_for_duration(duration_sec)
        transcript_payload: dict[str, Any] = {"segments": segments}
        _upsert_cache(
            video_id=vid,
            transcript=transcript_payload,
            stt_cost_usd=stt_cost,
            audio_duration_sec=duration_sec or None,
        )
        prefix = format_vietnamese_asr_supplement_for_video_extraction_vi(segments)
        return (prefix, stt_cost if stt_cost > 0 else 0.0)
    finally:
        if wav_path is not None and wav_path.exists():
            try:
                wav_path.unlink()
            except OSError:
                pass
