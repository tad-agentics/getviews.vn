"""Centralized environment-variable configuration using pydantic-settings.

Validates all required env vars at process startup. Misconfigured deployments
fail fast with a clear error message rather than crashing at first use.

Usage:
    from getviews_pipeline.settings import settings

    api_key = settings.gemini_api_key  # guaranteed non-empty at startup
    url = settings.supabase_url

Relationship to config.py:
    config.py imports from here for the critical fields (GEMINI_API_KEY, etc.)
    and retains its computed constants (derived URLs, fallback lists, etc.).
    Scattered os.environ.get calls in business-logic modules should gradually
    be migrated to import from settings instead.
"""

from __future__ import annotations

import logging
import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class _PipelineSettings(BaseSettings):
    """All environment variables for the GetViews Cloud Run pipeline.

    Fields WITHOUT a default are REQUIRED and cause an immediate startup
    failure if unset (fail-fast). Fields with defaults are optional tunables.

    Environment variable names: uppercase of the field name (pydantic-settings
    default). Case-insensitive on most platforms — use the canonical uppercase
    form in .env files and Cloud Run environment config.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # don't error on unrecognised env vars (other services share the env)
    )

    # ── Supabase ───────────────────────────────────────────────────────────
    supabase_url: str = Field(default="", description="Supabase project URL (https://<ref>.supabase.co)")
    supabase_anon_key: str = Field(default="", description="Supabase publishable anon key (JWT)")
    supabase_service_role_key: str = Field(default="", description="Supabase service role key — server-only, never in client bundle")
    supabase_jwt_secret: str = Field(default="", description="HS256 JWT secret — used as fallback when JWKS unavailable")
    supabase_jwks_url: str = Field(default="", description="Explicit JWKS URL override; derived from supabase_url when empty")

    # ── Gemini ─────────────────────────────────────────────────────────────
    gemini_api_key: str = Field(default="", description="Gemini API key — required for all video analysis and synthesis")
    gemini_model: str = Field(default="gemini-3.1-flash-lite", description="Default Gemini model slug")
    gemini_extraction_model: str = Field(default="", description="Model for frame extraction; defaults to gemini_model")
    gemini_synthesis_model: str = Field(default="", description="Model for Vietnamese narrative synthesis; defaults to gemini_model")
    gemini_knowledge_model: str = Field(default="", description="Model for knowledge Q&A; defaults to gemini_extraction_model")
    gemini_diagnosis_model: str = Field(default="", description="Text-only diagnosis pass; defaults to gemini_synthesis_model")
    gemini_intent_model: str = Field(default="", description="Intent classifier; defaults to gemini_knowledge_model")
    gemini_extraction_fallbacks: str = Field(default="", description="Comma-separated fallback model names for extraction")
    gemini_synthesis_fallbacks: str = Field(default="", description="Comma-separated fallback model names for synthesis")
    gemini_knowledge_fallbacks: str = Field(default="", description="Comma-separated fallback model names for knowledge")
    gemini_temperature: str = Field(default="", description="Legacy override; if set, overrides both extraction + synthesis temperatures")
    gemini_extraction_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    gemini_synthesis_temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    gemini_video_media_resolution: str = Field(default="", description="low|medium|high|unspecified — Gemini video resolution hint")
    gemini_video_analysis_hard_timeout_sec: float = Field(default=120.0, ge=10.0)
    gemini_video_download_timeout_sec: float = Field(default=90.0, ge=10.0)
    gemini_video_diagnosis_hard_timeout_sec: float = Field(default=120.0, ge=10.0)
    gemini_concurrency: int = Field(default=4, ge=1, le=32)

    # Global Gemini cost ceiling
    gemini_daily_usd_max: float = Field(default=0.0, ge=0.0, description="USD ceiling per UTC day; 0 = unlimited")
    gemini_daily_usd_enforce: bool = Field(default=False, description="Block calls when ceiling hit (else log-only)")
    gemini_daily_usd_cache_sec: int = Field(default=60, ge=1)

    # ── EnsembleData ───────────────────────────────────────────────────────
    ensemble_data_api_key: str = Field(default="", alias="ensemble_data_api_key", description="EnsembleData API key")
    ensembledata_api_token: str = Field(default="", description="Legacy alias for ensemble_data_api_key")
    ed_batch_daily_request_max: int = Field(default=0, ge=0, description="Max EnsembleData requests per UTC day; 0 = unlimited")
    ed_batch_budget_enforce: bool = Field(default=False)
    ed_unit_keyword_search: float = Field(default=1.0, ge=0.0)
    ed_unit_hashtag_posts: float = Field(default=1.0, ge=0.0)
    ed_unit_post_info: float = Field(default=1.0, ge=0.0)
    ed_unit_post_multi_info: float = Field(default=1.0, ge=0.0)
    ed_unit_user_posts: float = Field(default=1.0, ge=0.0)
    ed_unit_user_search: float = Field(default=1.0, ge=0.0)
    ed_unit_post_comments: float = Field(default=1.0, ge=0.0)
    ensemble_user_path_cache_ttl_sec: int = Field(default=300, ge=0)
    ensemble_user_path_cache_max: int = Field(default=2000, ge=0)
    keyword_search_author_stats: bool = Field(default=False)

    # ── TikHub (Douyin) ────────────────────────────────────────────────────
    tikhub_base_url: str = Field(default="https://api.tikhub.io")
    tikhub_api_key: str = Field(default="")
    tikhub_request_timeout_sec: float = Field(default=20.0, ge=1.0)
    tikhub_douyin_daily_request_max: int = Field(default=50, ge=0)

    # ── Corpus ingest ──────────────────────────────────────────────────────
    batch_videos_per_niche: int = Field(default=30, ge=1)
    batch_recency_days: int = Field(default=30, ge=1)
    corpus_target_per_niche: int = Field(default=200, ge=1)
    thin_niche_max_multiplier: float = Field(default=3.0, ge=1.0)
    batch_priority_niche_ids: str = Field(default="3", description="Comma-separated niche IDs for priority ingest")
    batch_priority_niche_vpn_floor: int = Field(default=35, ge=0)
    batch_priority_niche_max_vpn: int = Field(default=90, ge=1)
    batch_max_failures: int = Field(default=3, ge=0)
    batch_concurrency: int = Field(default=4, ge=1, le=32)
    batch_min_views: int = Field(default=20_000, ge=0)
    reference_ingest_min_views: int = Field(
        default=100_000,
        ge=0,
        description="Min play_count to enqueue live reference videos into corpus_ingest_queue",
    )
    batch_min_er: float = Field(default=2.0, ge=0.0)
    batch_keyword_pages: int = Field(default=2, ge=1)
    batch_carousels_per_niche: int = Field(default=3, ge=0)
    batch_carousels_by_niche: str = Field(
        default="",
        description=(
            "ME-18 optional: per legacy niche_id carousel cap, e.g. 2:8,3:6 — "
            "empty = use batch_carousels_per_niche for all; 0 disables carousels for that niche"
        ),
    )
    batch_carousel_min_likes: int = Field(default=1000, ge=0)
    batch_hashtag_fetch_limit: int = Field(default=15, ge=1)
    batch_hashtag_fetch_by_niche: str = Field(default="")
    reingest_multi_chunk: int = Field(default=12, ge=1)
    classifier_gemini_daily_max: int = Field(default=0, ge=0)
    corpus_legacy_carousel_hashtag_fetch: bool = Field(default=False)

    # ── Batch secret (admin auth) ──────────────────────────────────────────
    batch_secret: str = Field(default="", description="Shared secret for /batch/* and /admin/* routes")

    # ── Network / proxy ────────────────────────────────────────────────────
    residential_proxy_url: str = Field(default="", description="http://user:pass@host:port for TikTok CDN downloads")

    # ── Cloudflare R2 ──────────────────────────────────────────────────────
    r2_account_id: str = Field(default="")
    r2_access_key_id: str = Field(default="")
    r2_secret_access_key: str = Field(default="")
    r2_bucket_name: str = Field(default="getviews-frames")
    r2_public_url: str = Field(default="")
    r2_video_public_url: str = Field(default="")

    # ── Carousel extraction ────────────────────────────────────────────────
    carousel_extract_max_slides: int = Field(default=35, ge=1)
    carousel_max_slides: int = Field(default=10, ge=1)
    carousel_max_image_bytes: int = Field(default=15 * 1024 * 1024, ge=1)

    # ── Adaptive hashtag ──────────────────────────────────────────────────
    adaptive_hashtag_min_fetch: int = Field(default=2, ge=0)
    hashtag_yield_threshold: int = Field(default=1, ge=0)

    # ── Video flop thresholds (tunable) ───────────────────────────────────
    nicheless_flop_views_floor: int = Field(default=5000, ge=0)
    nicheless_flop_views_loose: int = Field(default=20000, ge=0)
    nicheless_flop_er_floor: float = Field(default=1.5, ge=0.0)

    # ── FFmpeg ─────────────────────────────────────────────────────────────
    ffmpeg_frame_timeout_sec: int = Field(default=120, ge=30)
    ffmpeg_frame_fallback_scale_width: int = Field(default=480, ge=160)

    # ── Cross-creator ──────────────────────────────────────────────────────
    cross_creator_lookback_days: int = Field(default=90, ge=1)
    cross_creator_insert_chunk: int = Field(default=500, ge=1)

    # ── Douyin ingest ──────────────────────────────────────────────────────
    batch_douyin_concurrency: int = Field(default=2, ge=1, le=32)
    batch_douyin_min_views: int = Field(default=100000, ge=0)
    batch_douyin_min_er: float = Field(default=2.5, ge=0.0)
    batch_douyin_hashtag_fetch_limit: int = Field(default=3, ge=1)
    batch_douyin_videos_per_niche: int = Field(default=5, ge=1)

    # ── Resend ─────────────────────────────────────────────────────────────
    resend_api_key: str = Field(default="")

    # ── Service role selector ──────────────────────────────────────────────
    service_role: str = Field(default="", description="'batch' or 'user' — controls which routes are active")

    # ── OpenTelemetry (Phase 2.1) ──────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = Field(default="", description="OTLP endpoint for Cloud Trace")
    gcp_project_id: str = Field(default="", description="GCP project ID for Cloud Trace export")

    # ── Computed properties ─────────────────────────────────────────────────

    @property
    def resolved_supabase_jwks_url(self) -> str | None:
        """JWKS URL: explicit override → derive from supabase_url → None."""
        explicit = self.supabase_jwks_url.strip()
        if explicit:
            return explicit
        base = self.supabase_url.strip().rstrip("/")
        if base:
            return f"{base}/auth/v1/.well-known/jwks.json"
        return None

    @property
    def effective_ensembledata_token(self) -> str:
        """Resolve either ENSEMBLE_DATA_API_KEY or legacy ENSEMBLEDATA_API_TOKEN."""
        return (self.ensemble_data_api_key or self.ensembledata_api_token).strip()

    @property
    def effective_gemini_extraction_model(self) -> str:
        return self.gemini_extraction_model.strip() or self.gemini_model

    @property
    def effective_gemini_synthesis_model(self) -> str:
        return self.gemini_synthesis_model.strip() or self.gemini_model

    @property
    def effective_gemini_knowledge_model(self) -> str:
        return self.gemini_knowledge_model.strip() or self.effective_gemini_extraction_model

    @property
    def effective_gemini_diagnosis_model(self) -> str | None:
        return self.gemini_diagnosis_model.strip() or None

    @property
    def effective_gemini_intent_model(self) -> str:
        return self.gemini_intent_model.strip() or self.effective_gemini_knowledge_model

    @property
    def effective_gemini_extraction_temperature(self) -> float:
        if self.gemini_temperature.strip():
            try:
                return float(self.gemini_temperature)
            except (TypeError, ValueError):
                pass
        return self.gemini_extraction_temperature

    @property
    def effective_gemini_synthesis_temperature(self) -> float:
        if self.gemini_temperature.strip():
            try:
                return float(self.gemini_temperature)
            except (TypeError, ValueError):
                pass
        return self.gemini_synthesis_temperature

    @property
    def gemini_extraction_fallbacks_list(self) -> list[str]:
        return [s.strip() for s in self.gemini_extraction_fallbacks.split(",") if s.strip()]

    @property
    def gemini_synthesis_fallbacks_list(self) -> list[str]:
        return [s.strip() for s in self.gemini_synthesis_fallbacks.split(",") if s.strip()]

    @property
    def gemini_knowledge_fallbacks_list(self) -> list[str]:
        return [s.strip() for s in self.gemini_knowledge_fallbacks.split(",") if s.strip()]

    @property
    def batch_priority_niche_ids_list(self) -> list[int]:
        result: list[int] = []
        for s in self.batch_priority_niche_ids.split(","):
            s = s.strip()
            if s.isdigit():
                result.append(int(s))
        return result

    # ── Startup validation ──────────────────────────────────────────────────

    def warn_unbounded_budgets(self) -> None:
        """Log warnings for uncapped production budgets. Called at startup."""
        if self.ed_batch_daily_request_max <= 0:
            logger.warning(
                "[budget] ED_BATCH_DAILY_REQUEST_MAX=0 (unlimited). "
                "Set a per-day cap to protect the EnsembleData budget."
            )
        elif not self.ed_batch_budget_enforce:
            logger.warning(
                "[budget] ED_BATCH_DAILY_REQUEST_MAX=%d but ED_BATCH_BUDGET_ENFORCE=false "
                "(log-only). Set ED_BATCH_BUDGET_ENFORCE=true to enforce the cap.",
                self.ed_batch_daily_request_max,
            )
        if self.classifier_gemini_daily_max <= 0:
            logger.warning(
                "[budget] CLASSIFIER_GEMINI_DAILY_MAX=0 (unlimited). "
                "Tier-3 intent classification is uncapped."
            )
        if self.gemini_daily_usd_max <= 0:
            logger.warning(
                "[budget] GEMINI_DAILY_USD_MAX=0 (unlimited). "
                "Global Gemini spend has no daily ceiling — set a USD cap to "
                "protect the ~$70/mo target documented in CLAUDE.md."
            )
        elif not self.gemini_daily_usd_enforce:
            logger.warning(
                "[budget] GEMINI_DAILY_USD_MAX=$%.2f but GEMINI_DAILY_USD_ENFORCE=false "
                "(log-only). Set GEMINI_DAILY_USD_ENFORCE=true to block calls "
                "once the cap is hit.",
                self.gemini_daily_usd_max,
            )
        if not self.residential_proxy_url:
            logger.warning(
                "[net] RESIDENTIAL_PROXY_URL is unset. TikTok CDN downloads will "
                "go directly from Cloud Run datacenter IPs and may be blocked."
            )

    def require_gemini_api_key(self) -> str:
        """Return the Gemini API key or raise ValueError (fail-fast sentinel)."""
        key = (os.environ.get("GEMINI_API_KEY") or self.gemini_api_key or "").strip()
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")
        return key

    def require_ensembledata_token(self) -> str:
        """Return the EnsembleData token or raise ValueError."""
        token = self.effective_ensembledata_token
        if not token:
            raise ValueError("ENSEMBLE_DATA_API_KEY / ENSEMBLEDATA_API_TOKEN is not set")
        return token


# ── Module-level singleton ──────────────────────────────────────────────────
# Instantiated once at import time; any missing/invalid field raises
# pydantic.ValidationError immediately (fail-fast at boot).
#
# In tests, override individual fields by setting env vars before importing,
# or patch settings.* attributes directly. The .env file is loaded automatically
# when running the service locally.

try:
    settings = _PipelineSettings()
except Exception as _boot_exc:  # pragma: no cover
    # Re-raise with a friendlier message that names the misconfigured field.
    raise RuntimeError(
        f"[settings] Pipeline misconfigured at startup — fix the environment variable and restart.\n"
        f"Detail: {_boot_exc}"
    ) from _boot_exc
