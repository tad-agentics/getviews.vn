"""Shared TikTok post analysis: fetch by URL or analyze raw aweme (video / carousel)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.config import CAROUSEL_EXTRACT_MAX_SLIDES, CAROUSEL_MAX_SLIDES
from getviews_pipeline.corpus_context import get_cached_analysis
from getviews_pipeline.gemini import analyze_carousel, analyze_video, synthesize_diagnosis
from getviews_pipeline.models import (
    CarouselAnalyzeResult,
    ContentType,
    VideoAnalyzeResult,
    VideoMetadata,
)
from getviews_pipeline.runtime import run_sync

logger = logging.getLogger(__name__)


async def _finish_analysis(
    *,
    metadata: VideoMetadata,
    analysis_obj: Any,
    metadata_for_diagnosis: dict[str, Any],
    include_diagnosis: bool,
) -> dict:
    content_type: ContentType = metadata.content_type
    if include_diagnosis:
        try:
            diagnosis = await run_sync(
                synthesize_diagnosis,
                analysis_obj.model_dump(),
                metadata_for_diagnosis,
                content_type,
            )
        except Exception as e:
            logger.warning("Diagnosis synthesis failed: %s", e)
            diagnosis = (
                "Synthesis could not be completed; structured `analysis` is still "
                "available.\n\n"
                f"Reason: {e}"
            )
    else:
        diagnosis = (
            "Diagnosis skipped (`include_diagnosis=false`) for faster results. "
            "Structured `analysis` is complete; re-run with diagnosis enabled for "
            "strategist markdown."
        )
    if content_type == "carousel":
        return CarouselAnalyzeResult(
            metadata=metadata,
            analysis=analysis_obj,
            diagnosis=diagnosis,
        ).model_dump()
    return VideoAnalyzeResult(
        metadata=metadata,
        analysis=analysis_obj,
        diagnosis=diagnosis,
    ).model_dump()


async def _analyze_video(
    *,
    metadata: VideoMetadata,
    video_urls: list[str],
    include_diagnosis: bool,
) -> dict:
    video_path: Path | None = None
    try:
        try:
            video_path = await ensemble.download_video(video_urls)
        except Exception as e:
            return {"error": str(e), "metadata": metadata.model_dump()}
        try:
            analysis = await run_sync(analyze_video, video_path)
        except Exception as e:
            return {"error": str(e), "metadata": metadata.model_dump()}
        return await _finish_analysis(
            metadata=metadata,
            analysis_obj=analysis,
            metadata_for_diagnosis=metadata.model_dump(),
            include_diagnosis=include_diagnosis,
        )
    finally:
        if video_path is not None and video_path.exists():
            try:
                video_path.unlink()
            except OSError:
                pass


async def _analyze_carousel(
    *,
    aweme: dict[str, Any],
    metadata: VideoMetadata,
    include_diagnosis: bool,
) -> dict:
    vid = str(aweme.get("aweme_id", "") or "")
    url_lists = ensemble.extract_image_url_lists(aweme)
    if not url_lists:
        logger.error(
            "[carousel] video_id=%s — aweme_type=2 but no per-slide CDN URLs in "
            "image_post_info; EnsembleData may not recognize this /photo/ URL format",
            vid,
        )
        return {
            "error": "carousel_no_images",
            "error_message": (
                "Không thể tải carousel này — EnsembleData không trả về ảnh slide. "
                "Thử lại hoặc dán link khác nha."
            ),
            "metadata": metadata.model_dump(),
        }

    total_slides = metadata.slide_count or len(url_lists)
    fetch_lists = url_lists[:CAROUSEL_MAX_SLIDES]
    limit_note = ""
    meta_diag = metadata.model_dump()

    if total_slides > CAROUSEL_EXTRACT_MAX_SLIDES:
        limit_note += (
            f"\n\nThis post has {total_slides} slides; we scanned the first "
            f"{CAROUSEL_EXTRACT_MAX_SLIDES} slide positions for CDN URLs, and "
            f"{len(url_lists)} had usable URLs and were extracted for analysis.\n"
        )
        meta_diag = {
            **meta_diag,
            "carousel_slides_total": total_slides,
            "carousel_slides_extracted": len(url_lists),
        }

    if len(fetch_lists) < len(url_lists):
        limit_note += (
            f"\nOnly the first {len(fetch_lists)} extracted slides are attached "
            f"(CAROUSEL_MAX_SLIDES={CAROUSEL_MAX_SLIDES}).\n"
        )
        meta_diag = {**meta_diag, "carousel_slides_attached": len(fetch_lists)}

    carousel_temp_paths: list[Path] = []
    try:
        try:
            downloaded, failed_indices = await ensemble.download_images(fetch_lists)
        except Exception as e:
            logger.error(
                "[carousel] video_id=%s — slide download failed: %s",
                vid,
                e,
                exc_info=True,
            )
            return {
                "error": "carousel_download_failed",
                "error_message": (
                    "Không tải được ảnh carousel — CDN bị chặn hoặc link hết hạn. "
                    "Thử lại hoặc dán link khác nha."
                ),
                "metadata": metadata.model_dump(),
            }

        carousel_temp_paths = [p for _, p, _ in downloaded]

        if failed_indices:
            meta_diag = {
                **meta_diag,
                "carousel_slides_download_failed_indices": failed_indices,
            }
            limit_note += (
                "\nCDN download failed for slide indices "
                f"{failed_indices} (0-based, relative to extracted set); "
                "attached images are only the successfully downloaded slides, in order.\n"
            )
            logger.warning(
                "[carousel] video_id=%s — %d slide(s) failed CDN download: indices %s",
                vid,
                len(failed_indices),
                failed_indices,
            )

        if not downloaded:
            logger.error(
                "[carousel] video_id=%s — all slides failed CDN download", vid
            )
            return {
                "error": "carousel_all_slides_failed",
                "error_message": (
                    "Không tải được ảnh nào từ carousel — CDN bị chặn. "
                    "Thử lại sau hoặc dán link khác nha."
                ),
                "metadata": metadata.model_dump(),
            }

        try:
            source_indices = [i for i, _, _ in downloaded]
            slide_bytes = [(p.read_bytes(), m) for _, p, m in downloaded]
            analysis = await run_sync(
                analyze_carousel,
                slide_bytes,
                limit_note,
                source_indices,
            )
        except Exception as e:
            logger.error(
                "[carousel] video_id=%s — Gemini analysis failed: %s",
                vid,
                e,
                exc_info=True,
            )
            return {
                "error": "carousel_analysis_failed",
                "error_message": (
                    "Gemini không phân tích được carousel này. "
                    "Thử lại sau ít phút nha."
                ),
                "metadata": metadata.model_dump(),
            }

        analyzed_count = len(slide_bytes)
        metadata_out = metadata.model_copy(update={"slide_count": analyzed_count})
        meta_diag["slide_count"] = analyzed_count
        if total_slides > analyzed_count:
            meta_diag["carousel_slides_total"] = total_slides

        return await _finish_analysis(
            metadata=metadata_out,
            analysis_obj=analysis,
            metadata_for_diagnosis=meta_diag,
            include_diagnosis=include_diagnosis,
        )
    finally:
        for p in carousel_temp_paths:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass


async def analyze_aweme_from_path(
    aweme: dict[str, Any],
    video_path: Path,
    *,
    include_diagnosis: bool = False,
) -> dict:
    """Analyze a raw aweme using an already-downloaded video file.

    Skips the ``ensemble.download_video()`` call — caller owns the file
    and is responsible for cleanup. Used by corpus_ingest to share a single
    proxy download across Gemini analysis and R2 frame extraction.

    Only supports video content type (carousels have no local path to pass).
    Returns an error dict if the aweme is a carousel or the path is missing.
    """
    ct = ensemble.detect_content_type(aweme)
    if ct == "carousel":
        return {
            "error": "analyze_aweme_from_path does not support carousels",
            "metadata": ensemble.parse_metadata(aweme).model_dump(),
        }

    if not video_path.exists():
        return {
            "error": f"video_path {video_path} does not exist",
            "metadata": ensemble.parse_metadata(aweme).model_dump(),
        }

    metadata = ensemble.parse_metadata(aweme)
    try:
        analysis = await run_sync(analyze_video, video_path)
    except Exception as e:
        return {"error": str(e), "metadata": metadata.model_dump()}

    return await _finish_analysis(
        metadata=metadata,
        analysis_obj=analysis,
        metadata_for_diagnosis=metadata.model_dump(),
        include_diagnosis=include_diagnosis,
    )


async def analyze_aweme(
    aweme: dict[str, Any],
    *,
    include_diagnosis: bool = True,
    full_analyses: dict[str, dict[str, Any]] | None = None,
) -> dict:
    """Analyze a raw aweme dict; reuse ``full_analyses[video_id]`` when present (§10 Rule 12)."""
    vid = str(aweme.get("aweme_id", "") or "")

    # 1. Session cache — same video seen earlier in this conversation
    if full_analyses is not None and vid and vid in full_analyses:
        cached = full_analyses[vid]
        return dict(cached)

    # 2. Corpus cache — video already analyzed by batch ingest or a previous user.
    #    Skip download + Gemini call entirely; use stored analysis_json.
    if vid:
        corpus_hit = await get_cached_analysis(vid)
        if corpus_hit:
            metadata = ensemble.parse_metadata(aweme)
            result = {
                "analysis": corpus_hit["analysis"],
                "metadata": metadata.model_dump(),
                "_from_corpus_cache": True,
            }
            if full_analyses is not None:
                full_analyses[vid] = result
            return result

    metadata = ensemble.parse_metadata(aweme)
    ct = ensemble.detect_content_type(aweme)

    if ct == "carousel":
        result = await _analyze_carousel(
            aweme=aweme,
            metadata=metadata,
            include_diagnosis=include_diagnosis,
        )
    else:
        video_urls = ensemble.extract_video_urls(aweme)
        if video_urls:
            result = await _analyze_video(
                metadata=metadata,
                video_urls=video_urls,
                include_diagnosis=include_diagnosis,
            )
        else:
            result = {
                "error": "No video or photo carousel URLs in post response",
                "metadata": metadata.model_dump(),
            }

    if (
        full_analyses is not None
        and vid
        and "error" not in result
        and "analysis" in result
    ):
        full_analyses[vid] = result
    return result


async def analyze_tiktok_url(
    url: str,
    *,
    include_diagnosis: bool = True,
    full_analyses: dict[str, dict[str, Any]] | None = None,
) -> dict:
    """Fetch post by URL then analyze (same contract as legacy ``_analyze_core``)."""
    aweme = await ensemble.fetch_post_info(url)
    return await analyze_aweme(
        aweme,
        include_diagnosis=include_diagnosis,
        full_analyses=full_analyses,
    )
