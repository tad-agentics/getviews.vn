"""HI-13 Gemini Batch extraction for Douyin ingest (Phase 3a).

Reuses platform-agnostic batch primitives from ``gemini.py``. Skips vi-VN
ASR — Douyin audio is Chinese; prepends the CN caption instead. Sync
fallback to ``async_run_extraction_core`` when batch fails per video.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.config import (
    CORPUS_BATCH_POLL_INTERVAL_SEC,
    CORPUS_BATCH_POLL_MAX_SEC,
    DOUYIN_CDN_HEADERS,
    DOUYIN_VIDEO_DOWNLOAD_MAX_BYTES,
    GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
)
from getviews_pipeline.douyin_translator import translate_douyin_caption
from getviews_pipeline.gemini import (
    build_video_corpus_batch_jsonl_record,
    parse_batch_extraction_analysis_json,
    run_corpus_extraction_batch_file_job,
    upload_local_video_file_active,
)
from getviews_pipeline.models import VideoAnalysis
from getviews_pipeline.r2 import (
    bank_local_video_to_r2,
    extract_and_upload,
    extract_and_upload_scene_frames,
    r2_configured,
)
from getviews_pipeline.runtime import get_analysis_semaphore
from getviews_pipeline.vietnamese_slang import merge_lexicon_slang_into_video_analysis_dict

logger = logging.getLogger(__name__)

AnalyzeTranslateResult = tuple[
    dict[str, Any],
    list[str],
    list[tuple[int, str]],
    dict[str, Any] | None,
    str | None,
]


def build_douyin_caption_extraction_prefix(desc_zh: str, hashtags: list[str]) -> str:
    """CN caption prefix for Douyin batch extraction (no vi-VN ASR)."""
    lines = ["[Douyin caption — Chinese]", (desc_zh or "").strip()]
    tags = [str(t).strip() for t in hashtags if str(t).strip()]
    if tags:
        lines.append("Hashtags: " + " ".join(tags))
    return "\n".join(lines).strip()


@dataclass
class _DouyinPrep:
    idx: int
    aweme: dict[str, Any]
    video_path: Path
    video_id: str
    file_resource: Any
    gemini_upload_name: str
    frame_urls: list[str]
    caption_prefix: str
    translation_task: asyncio.Task[dict[str, Any] | None]


async def analyze_douyin_awemes_gemini_batch(
    awemes: list[dict[str, Any]],
    *,
    niche_name: str,
) -> list[AnalyzeTranslateResult | BaseException]:
    """Batch-extract Douyin awemes; return shape matches ``_analyze_translate_one``."""
    n = len(awemes)
    if n == 0:
        return []

    sem = get_analysis_semaphore()
    loop = asyncio.get_event_loop()

    async def prep_one(i: int, aweme: dict[str, Any]) -> tuple[int, Any]:
        async with sem:
            try:
                ct = ensemble.detect_content_type(aweme)
                if ct == "carousel":
                    return i, RuntimeError("carousel_not_batch_supported")

                vid = str(aweme.get("aweme_id", "") or "")
                video_urls = ensemble.extract_video_urls(aweme)
                if not video_urls:
                    return i, RuntimeError("No video URLs in aweme")

                video_path = await ensemble.download_video(
                    video_urls,
                    headers=DOUYIN_CDN_HEADERS,
                    max_bytes=DOUYIN_VIDEO_DOWNLOAD_MAX_BYTES,
                )
                desc_zh = str(aweme.get("desc", "") or "")
                creator = str(((aweme.get("author") or {}).get("unique_id")) or "")
                metadata = ensemble.parse_metadata(aweme)
                caption_prefix = build_douyin_caption_extraction_prefix(
                    desc_zh,
                    metadata.hashtags,
                )

                translation_task = asyncio.create_task(
                    loop.run_in_executor(
                        None,
                        lambda: translate_douyin_caption(desc_zh, creator_handle=creator),
                    )
                )

                async def _noop_frames() -> list[str]:
                    return []

                frame_coro = (
                    extract_and_upload(video_path, vid)
                    if r2_configured()
                    else _noop_frames()
                )
                file_resource, frame_urls = await asyncio.gather(
                    loop.run_in_executor(
                        None,
                        upload_local_video_file_active,
                        video_path,
                    ),
                    frame_coro,
                )
                gname = getattr(file_resource, "name", None) or ""
                return i, _DouyinPrep(
                    idx=i,
                    aweme=aweme,
                    video_path=video_path,
                    video_id=vid,
                    file_resource=file_resource,
                    gemini_upload_name=gname,
                    frame_urls=frame_urls if isinstance(frame_urls, list) else [],
                    caption_prefix=caption_prefix,
                    translation_task=translation_task,
                )
            except Exception as exc:  # noqa: BLE001
                return i, exc

    prep_pairs = await asyncio.gather(*[prep_one(k, awemes[k]) for k in range(n)])
    preps: list[Any] = [None] * n
    for idx, item in prep_pairs:
        preps[idx] = item

    records: list[dict[str, Any]] = []
    gemini_names: list[str] = []
    for i in range(n):
        entry = preps[i]
        if not isinstance(entry, _DouyinPrep):
            continue
        records.append(
            build_video_corpus_batch_jsonl_record(
                entry.video_id,
                entry.file_resource,
                supplemental_user_prefix=entry.caption_prefix or None,
            )
        )
        gemini_names.append(entry.gemini_upload_name)

    batch_map: dict[str, dict[str, Any]] = {}
    if records:
        safe = re.sub(r"[^\w\-]+", "_", niche_name)[:40]
        display_name = f"douyin-{safe}-{int(time.time())}"
        batch_out = await loop.run_in_executor(
            None,
            lambda: run_corpus_extraction_batch_file_job(
                records=records,
                display_name=display_name,
                poll_interval_s=CORPUS_BATCH_POLL_INTERVAL_SEC,
                poll_max_s=CORPUS_BATCH_POLL_MAX_SEC,
                gemini_file_names=gemini_names,
                gcp_stt_cost_by_video_id={},
            ),
        )
        if batch_out.get("ok") and isinstance(batch_out.get("by_video_id"), dict):
            batch_map = batch_out["by_video_id"]
        else:
            logger.warning(
                "[douyin-hi13] batch job failed niche=%s state=%s err=%s",
                niche_name,
                batch_out.get("state"),
                batch_out.get("job_error"),
            )

    results: list[AnalyzeTranslateResult | BaseException] = []
    for i in range(n):
        entry = preps[i]
        if isinstance(entry, BaseException):
            results.append(entry)
            continue
        if not isinstance(entry, _DouyinPrep):
            results.append(TypeError(f"batch prep unexpected {type(entry).__name__}"))
            continue

        p = entry
        vid = p.video_id
        aweme = p.aweme
        video_path = p.video_path
        frame_urls = p.frame_urls

        br = batch_map.get(vid)
        analysis_obj: VideoAnalysis | None = None
        if br and br.get("ok") and br.get("text"):
            try:
                raw = parse_batch_extraction_analysis_json(str(br["text"]))
                merge_lexicon_slang_into_video_analysis_dict(raw)
                analysis_obj = VideoAnalysis.model_validate(raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[douyin-hi13] batch JSON validate failed video_id=%s: %s",
                    vid,
                    exc,
                )
                analysis_obj = None

        if analysis_obj is None:
            try:
                from getviews_pipeline.services.extraction import async_run_extraction_core

                extraction_result = await asyncio.wait_for(
                    async_run_extraction_core(aweme, video_path),
                    timeout=GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
                )
                if extraction_result.error:
                    results.append(
                        {
                            "error": extraction_result.error,
                            "metadata": extraction_result.metadata.model_dump(),
                        }
                    )
                    try:
                        video_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    continue
                finished = {
                    "metadata": extraction_result.metadata.model_dump(),
                    "analysis": (
                        extraction_result.analysis.model_dump()
                        if extraction_result.analysis
                        else {}
                    ),
                    "content_type": extraction_result.content_type,
                    "transcript_quality": extraction_result.transcript_quality,
                    "entry_cost": extraction_result.entry_cost,
                }
            except Exception as exc:  # noqa: BLE001
                results.append(exc)
                try:
                    video_path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue
        else:
            metadata = ensemble.parse_metadata(aweme)
            try:
                from getviews_pipeline.analysis_core import _finish_analysis

                finished = await asyncio.wait_for(
                    _finish_analysis(
                        metadata=metadata,
                        analysis_obj=analysis_obj,
                        metadata_for_diagnosis=metadata.model_dump(),
                        include_diagnosis=False,
                    ),
                    timeout=GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
                )
            except Exception as exc:  # noqa: BLE001
                results.append(exc)
                try:
                    video_path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue

        scene_frame_pairs: list[tuple[int, str]] = []
        if r2_configured():
            scenes = (finished.get("analysis") or {}).get("scenes") or []
            if scenes:
                try:
                    scene_frame_pairs = await extract_and_upload_scene_frames(
                        video_path,
                        vid,
                        scenes,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[douyin-hi13] scene frames failed %s: %s", vid, exc
                    )

        playback_url: str | None = None
        if r2_configured():
            try:
                playback_url = await loop.run_in_executor(
                    None,
                    lambda: bank_local_video_to_r2(
                        vid,
                        video_path,
                        max_bytes=DOUYIN_VIDEO_DOWNLOAD_MAX_BYTES,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[douyin-hi13] banking failed %s: %s", vid, exc)

        translation: dict[str, Any] | None = None
        try:
            translation = await p.translation_task
        except Exception as exc:  # noqa: BLE001
            logger.warning("[douyin-hi13] translation failed %s: %s", vid, exc)

        try:
            video_path.unlink(missing_ok=True)
        except OSError:
            pass

        results.append(
            (
                finished,
                frame_urls,
                scene_frame_pairs,
                translation,
                playback_url,
            )
        )

    return results
