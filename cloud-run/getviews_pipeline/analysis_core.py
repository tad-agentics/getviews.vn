"""Shared TikTok post analysis: fetch by URL or analyze raw aweme (video / carousel)."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from getviews_pipeline import ensemble
from getviews_pipeline.analysis_guards import (
    TRANSCRIPT_UNAVAILABLE_MARKER,
    apply_timestamp_guards,
    validate_transcript,
)
from getviews_pipeline.config import (
    CAROUSEL_EXTRACT_MAX_SLIDES,
    CAROUSEL_MAX_SLIDES,
    GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
    GEMINI_VIDEO_DIAGNOSIS_HARD_TIMEOUT_SEC,
    GEMINI_VIDEO_DOWNLOAD_TIMEOUT_SEC,
)
from getviews_pipeline.corpus_context import get_cached_analysis
from getviews_pipeline.entry_cost import score_entry_cost
from getviews_pipeline.gemini import analyze_carousel, analyze_video, synthesize_diagnosis
from getviews_pipeline.models import (
    CarouselAnalyzeResult,
    ContentType,
    VideoAnalyzeResult,
    VideoMetadata,
)
from getviews_pipeline.runtime import run_sync
from getviews_pipeline.services.asr_vietnamese import sync_prepare_vietnamese_asr_supplement

logger = logging.getLogger(__name__)


def detect_language_market_mismatch(hook_text: str, target_market: str = "vi") -> dict | None:
    """Detect if hook/caption language doesn't match the target market."""
    try:
        from langdetect import DetectorFactory, detect
    except ImportError:
        return None

    # langdetect is probabilistic by default — same input flaps lang label
    # between calls. Pin the seed so a hook either is or isn't flagged,
    # consistently across requests.
    DetectorFactory.seed = 0

    cleaned = re.sub(r"#\S+|@\S+|https?://\S+", "", hook_text).strip()
    words = [w for w in cleaned.split() if re.search(r"[a-zA-ZÀ-ỹ]", w)]

    if len(words) < 4:
        return None

    try:
        lang = detect(cleaned)
    except Exception:
        return None

    if lang == target_market:
        return None

    return {
        "error_id": "lang_market_mismatch",
        "title": f"Hook dùng ngôn ngữ không phù hợp ({lang.upper()})",
        "detail": (
            f"Hook video dùng tiếng {lang.upper()} thay vì tiếng Việt. "
            "Tệp người xem Việt Nam scroll qua nội dung không đọc được trong 0.5 giây đầu."
        ),
        "fix": (
            "Viết lại hook bằng tiếng Việt với góc nhìn cụ thể về nhu cầu tệp. "
            "Thay generic call-out bằng POV hoặc câu hỏi gây tò mò."
        ),
        "sev": "high",
        "t": 0.0,
        "end": 3.0,
    }


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
            diagnosis = await asyncio.wait_for(
                run_sync(
                    synthesize_diagnosis,
                    analysis_obj.model_dump(),
                    metadata_for_diagnosis,
                    content_type,
                ),
                timeout=GEMINI_VIDEO_DIAGNOSIS_HARD_TIMEOUT_SEC,
            )
        except TimeoutError:
            logger.warning(
                "[analysis_core] diagnosis synthesis timed out after %.0fs",
                GEMINI_VIDEO_DIAGNOSIS_HARD_TIMEOUT_SEC,
            )
            diagnosis = (
                "Tổng hợp chẩn đoán mất quá lâu; dữ liệu phân tích cấu trúc (JSON) vẫn đầy đủ. "
                "Vui lòng thử lại."
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
    out = VideoAnalyzeResult(
        metadata=metadata,
        analysis=analysis_obj,
        diagnosis=diagnosis,
    ).model_dump()
    # Trust guards — run before downstream pipelines read the analysis dict.
    # Fail-soft throughout: a guard that raises never blocks the primary flow,
    # it just skips its own protection.
    analysis_dict = out.get("analysis") or {}
    try:
        apply_timestamp_guards(analysis_dict, getattr(metadata, "duration_sec", None))
    except Exception as exc:  # pragma: no cover — pure helper
        logger.warning("apply_timestamp_guards failed: %s", exc)
    try:
        transcript = str(analysis_dict.get("audio_transcript") or "")
        verdict = validate_transcript(transcript)
        if not verdict.ok:
            logger.warning(
                "[analysis_guards] transcript rejected reason=%s vi_ratio=%.3f — "
                "replacing with marker",
                verdict.reason, verdict.vi_ratio,
            )
            analysis_dict["audio_transcript"] = TRANSCRIPT_UNAVAILABLE_MARKER
        out["transcript_quality"] = verdict.asdict()
    except Exception as exc:  # pragma: no cover — pure helper
        logger.warning("validate_transcript failed: %s", exc)
    # Entry-cost badge (easy / medium / hard) — attached to every video analysis
    # so any downstream consumer (trend_spike card, content_directions reference,
    # competitor_profile card) can render it without re-deriving.
    try:
        tier, reasons = score_entry_cost(analysis_dict)
        out["entry_cost"] = {"tier": tier, "reasons": reasons}
    except Exception as exc:  # pragma: no cover — score_entry_cost is pure
        logger.warning("entry_cost scoring failed: %s", exc)
    return out


async def _analyze_video(
    *,
    metadata: VideoMetadata,
    video_urls: list[str],
    include_diagnosis: bool,
) -> dict:
    video_path: Path | None = None
    try:
        try:
            video_path = await asyncio.wait_for(
                ensemble.download_video(video_urls),
                timeout=GEMINI_VIDEO_DOWNLOAD_TIMEOUT_SEC,
            )
        except TimeoutError:
            logger.warning(
                "[analysis_core] video download timed out after %.0fs",
                GEMINI_VIDEO_DOWNLOAD_TIMEOUT_SEC,
            )
            return {
                "error": "Tải video TikTok mất quá lâu. Vui lòng thử lại hoặc kiểm tra mạng.",
                "metadata": metadata.model_dump(),
            }
        except Exception as e:
            return {"error": str(e), "metadata": metadata.model_dump()}
        try:
            loop = asyncio.get_event_loop()
            try:
                asr_prefix, stt_usd = await loop.run_in_executor(
                    None,
                    sync_prepare_vietnamese_asr_supplement,
                    video_path,
                    metadata.video_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[hi14] asr supplement prep failed: %s", exc)
                asr_prefix, stt_usd = "", None

            analysis = await asyncio.wait_for(
                run_sync(
                    analyze_video,
                    video_path,
                    supplemental_user_prefix=asr_prefix or None,
                    gcp_stt_cost_usd=stt_usd,
                ),
                timeout=GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
            )
        except TimeoutError:
            logger.warning(
                "[analysis_core] video extraction timed out after %.0fs",
                GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
            )
            return {
                "error": "Phân tích video mất quá lâu. Vui lòng thử lại hoặc dùng video ngắn hơn.",
                "metadata": metadata.model_dump(),
            }
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

    # Re-query fallback: URL-based lookups often return empty image_post_info for
    # /photo/ posts. Querying by native aweme_id (multi-info endpoint) populates
    # image_post_info.images more reliably — TikTok's CDN URL layout differs.
    if not url_lists and vid:
        logger.info(
            "[carousel] video_id=%s — empty image_post_info from URL lookup; "
            "re-fetching by aweme_id via fetch_post_multi_info",
            vid,
        )
        try:
            re_fetched = await ensemble.fetch_post_multi_info([vid])
            if re_fetched:
                aweme_refetch = re_fetched[0]
                url_lists = ensemble.extract_image_url_lists(aweme_refetch)
                if url_lists:
                    logger.info(
                        "[carousel] video_id=%s — re-fetch by aweme_id succeeded: %d slides",
                        vid,
                        len(url_lists),
                    )
                    # Use re-fetched aweme for downstream slide processing.
                    aweme = aweme_refetch
                    # Re-parse metadata in case the re-fetch has richer fields.
                    metadata = ensemble.parse_metadata(aweme_refetch)
                else:
                    logger.warning(
                        "[carousel] video_id=%s — re-fetch by aweme_id: still no images",
                        vid,
                    )
        except Exception as exc:
            logger.warning(
                "[carousel] video_id=%s — re-fetch by aweme_id failed: %s",
                vid,
                exc,
            )

    if not url_lists:
        logger.error(
            "[carousel] video_id=%s — aweme_type=2 but no per-slide CDN URLs in "
            "image_post_info after URL + aweme_id re-query; EnsembleData gap",
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

        result = await _finish_analysis(
            metadata=metadata_out,
            analysis_obj=analysis,
            metadata_for_diagnosis=meta_diag,
            include_diagnosis=include_diagnosis,
        )

        # Upload slide[0] as the permanent thumbnail.
        # Carousels have no video to extract frame[0] from, so the slide images
        # that are already in memory here are the only zero-extra-cost source.
        # The resulting R2 URL is injected into the result dict so corpus_ingest
        # can write it to video_corpus.thumbnail_url without an extra CDN fetch.
        if vid and slide_bytes:
            try:
                from getviews_pipeline.r2 import r2_configured, upload_thumbnail_bytes
                if r2_configured():
                    first_bytes, first_mime = slide_bytes[0]
                    thumb_content_type = first_mime or "image/jpeg"
                    thumb_loop = asyncio.get_event_loop()
                    r2_thumb = await thumb_loop.run_in_executor(
                        None, upload_thumbnail_bytes, vid, first_bytes, thumb_content_type,
                    )
                    if r2_thumb:
                        result["r2_thumbnail_url"] = r2_thumb
                        logger.info(
                            "[carousel] video_id=%s — slide[0] uploaded as thumbnail: %s",
                            vid, r2_thumb,
                        )
            except Exception as exc:
                logger.warning(
                    "[carousel] video_id=%s — slide[0] thumbnail upload failed (non-fatal): %s",
                    vid, exc,
                )

        return result
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
        loop = asyncio.get_event_loop()
        try:
            asr_prefix, stt_usd = await loop.run_in_executor(
                None,
                sync_prepare_vietnamese_asr_supplement,
                video_path,
                metadata.video_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[hi14] asr supplement prep failed (from_path): %s", exc)
            asr_prefix, stt_usd = "", None

        analysis = await asyncio.wait_for(
            run_sync(
                analyze_video,
                video_path,
                supplemental_user_prefix=asr_prefix or None,
                gcp_stt_cost_usd=stt_usd,
            ),
            timeout=GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
        )
    except TimeoutError:
        logger.warning(
            "[analysis_core] video extraction timed out after %.0fs (from_path)",
            GEMINI_VIDEO_ANALYSIS_HARD_TIMEOUT_SEC,
        )
        return {
            "error": "Phân tích video mất quá lâu. Vui lòng thử lại hoặc dùng video ngắn hơn.",
            "metadata": metadata.model_dump(),
        }
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
    include_diagnosis: bool = False,
    full_analyses: dict[str, dict[str, Any]] | None = None,
    skip_corpus_cache: bool = False,
) -> dict:
    """Analyze a raw aweme dict; reuse ``full_analyses[video_id]`` when present (§10 Rule 12).

    include_diagnosis defaults to False — pipeline callers always pass it explicitly and
    diagnosis adds significant latency + token cost. Use analyze_tiktok_url() (which
    defaults to True) for standalone single-URL analysis where diagnosis is expected.

    skip_corpus_cache=True skips the get_cached_analysis() Supabase call. Use this when
    calling from within asyncio.run() (a new event loop), because get_cached_analysis uses
    the module-level _anon_client() which is bound to the main FastAPI event loop and will
    raise "Event loop is closed" when used from a different event loop.
    The on-demand path (_fetch_and_analyze_async) always sets skip_corpus_cache=True because
    the video is already known to not be in the corpus.
    """
    vid = str(aweme.get("aweme_id", "") or "")

    # 1. Session cache — same video seen earlier in this conversation
    if full_analyses is not None and vid and vid in full_analyses:
        cached = full_analyses[vid]
        return dict(cached)

    # 2. Corpus cache — video already analyzed by batch ingest or a previous user.
    #    Skip download + Gemini call entirely; use stored analysis_json.
    #    Skipped when skip_corpus_cache=True to avoid event-loop-closed errors when
    #    called from within asyncio.run() (the on-demand path).
    if vid and not skip_corpus_cache:
        corpus_hit = await get_cached_analysis(vid)
        if corpus_hit:
            metadata = ensemble.parse_metadata(aweme)
            result = {
                "content_type": metadata.content_type,
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
    with ensemble.ed_call_site("video_diagnosis.post_info"):
        aweme = await ensemble.fetch_post_info(url)
    return await analyze_aweme(
        aweme,
        include_diagnosis=include_diagnosis,
        full_analyses=full_analyses,
    )
