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
    # Defaults must mirror config.py GEMINI_DAILY_USD_MAX / _ENFORCE — the
    # enforcement path (gemini_cost.check_gemini_daily_budget) reads config.py,
    # this copy only drives startup warnings. They had drifted (0.0/False
    # here vs 15/True there), making the warning claim "unlimited" while the
    # cap was actually live — audit 2026-06-10 M-1.
    gemini_daily_usd_max: float = Field(default=15.0, ge=0.0, description="USD ceiling per UTC day; 0 = unlimited")
    gemini_daily_usd_enforce: bool = Field(default=True, description="Block calls when ceiling hit (else log-only)")
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
    tikhub_douyin_daily_request_max: int = Field(default=150, ge=0)

    # ── Corpus ingest ──────────────────────────────────────────────────────
    batch_videos_per_niche: int = Field(default=30, ge=1)
    batch_recency_days: int = Field(default=30, ge=1)
    corpus_target_per_niche: int = Field(default=200, ge=1)
    thin_niche_max_multiplier: float = Field(default=3.0, ge=1.0)
    batch_priority_niche_ids: str = Field(
        default="1,2,3,4,5,8,9,11",
        description="Comma-separated hero niche_taxonomy.id for priority ingest (Wave 2 §8.7)",
    )
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
    # ── Corpus ingest selection (instructiveness / purity) ─────────────────
    corpus_ingest_mode: str = Field(
        default="legacy",
        description="legacy | shadow | purity — see corpus-ingest-criteria-v1.md",
    )
    corpus_ingest_max_age_days: int = Field(
        default=0,
        ge=0,
        description="Tier 1 hard max post age (days); 0=off. Purity default 14 via env.",
    )
    corpus_relax_trigger_max: int = Field(default=5, ge=0)
    corpus_relax_view_floor_pct: float = Field(default=0.30, ge=0.0, le=1.0)
    corpus_hook_predict_penalty: float = Field(default=15.0, ge=0.0)
    corpus_velocity_gate_min: float = Field(default=0.15, ge=0.0)
    corpus_sound_organic_bonus: float = Field(default=1.0, ge=0.0)
    corpus_ingest_shadow_log: bool = Field(default=True)
    corpus_score_cohort: str = Field(
        default="class",
        description="legacy | class_shadow | class — instructiveness cohort axis",
    )
    live_cohort_class_first: bool = Field(
        default=True,
        description="When true, live benchmark prefers content_class_intelligence MV",
    )
    corpus_discovery_relax: bool = Field(
        default=False,
        description="ACQE Thin/Dormant: lower pre-pool floor, widen hashtag fetch",
    )
    corpus_ingest_loop: str = Field(
        default="class",
        description="niche | class — batch loop over niche_taxonomy vs content_class_ingest_targets",
    )
    corpus_write_niche_id: bool = Field(
        default=False,
        description="Phase 4: when false, batch upsert omits niche_id (class-only cohort)",
    )
    refresh_niche_intelligence_mv: bool = Field(
        default=False,
        description="Phase 4: when false, skip nightly refresh_niche_intelligence RPC",
    )
    corpus_boost_hard_reject: bool = Field(default=False)
    corpus_benchmark_window_days: int = Field(
        default=60,
        ge=7,
        le=180,
        description="content_class_intelligence MV indexed_at window (days)",
    )
    corpus_reference_fetch_days: int = Field(
        default=60,
        ge=7,
        le=180,
        description="Reference pool PostgREST query window (indexed_at)",
    )
    corpus_reference_pick_days: int = Field(
        default=60,
        ge=7,
        le=180,
        description="Proximity pick recency filter (posted_at, else indexed_at)",
    )
    corpus_citation_window_days: int = Field(
        default=60,
        ge=7,
        le=180,
        description="get_corpus_count + synthesis citation timeframe",
    )
    corpus_adaptive_max_days: int = Field(
        default=60,
        ge=7,
        le=180,
        description="Adaptive report window ladder cap (after 7/14/30)",
    )
    diagnosis_hook_leaderboard: bool = Field(
        default=True,
        description="Inject measured hook-effectiveness block into live diagnosis prompt",
    )
    diagnosis_comment_grounding: bool = Field(
        default=True,
        description="Inject comment_radar block into live diagnosis prompt",
    )
    diagnosis_retention_structural: bool = Field(
        default=True,
        description="Structure-driven retention curve + risk_events (else synthetic decay)",
    )
    signal_calibration_adaptive: bool = Field(
        default=True,
        description="Adopt corpus-learned viral weights + salience demotion + synthesis priors",
    )
    extraction_signals_v2: bool = Field(
        default=True,
        description="Ground Tier 1/2 extraction signals into diagnosis prose (shadow compute when off)",
    )
    extraction_audio_dsp: bool = Field(
        default=False,
        description="Audio DSP beat-sync + voice-energy (batch-only; Tier 3 deferred)",
    )
    diagnosis_voice_lint_runtime: bool = Field(
        default=True,
        description="Run lint_forbidden_copy on synthesis *_vi fields (log + soft-scrub)",
    )
    diagnosis_lead_lever: bool = Field(
        default=True,
        description="Emit lead_finding in diagnosis_vi JSON + elevate in FE",
    )
    diagnosis_wide_context: bool = Field(
        default=False,
        description="Widen USER_EVIDENCE_DIGEST (more scenes, full hook_timeline)",
    )
    diagnosis_salience_rank_only: bool = Field(
        default=True,
        description="Demote salience from emit-gate to ranking-only (no section cap drop)",
    )
    diagnosis_proposed_findings: bool = Field(
        default=False,
        description="Allow LLM-proposed findings beyond fired signals (lower confidence)",
    )
    corpus_postextract_hook_cap: int = Field(default=3, ge=1)
    corpus_hook_cap_breakout_bypass: float = Field(default=3.0, ge=0.0)
    corpus_purity_vpn_default: int = Field(default=15, ge=1)
    corpus_purity_pass_rate_vpn_bonus: int = Field(default=3, ge=0)
    corpus_max_per_creator: int = Field(default=2, ge=1)
    corpus_max_per_sound: int = Field(default=2, ge=1)
    corpus_convergence_min_gates: int = Field(default=3, ge=1, le=4)
    corpus_convergence_relaxed_min_gates: int = Field(default=2, ge=1, le=4)
    corpus_tier1_min_extract_floor: int = Field(default=3, ge=1)
    ed_batch_comment_fetch_enabled: bool = Field(default=False)
    ed_batch_comment_fetch_kill_pct: float = Field(default=15.0, ge=0.0, le=100.0)
    corpus_postextract_hard_reject: bool = Field(
        default=True,
        description="Tier 3a hard failures block upsert when true",
    )
    corpus_postextract_hook_cap_enforce: bool = Field(
        default=False,
        description="Tier 3b soft hook cap — enable via env when shadow/QA metrics pass",
    )
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
    getviews_deep_relax_salience: bool = Field(
        default=True,
        description="§4.3 — when true, SECTION_EMIT_THRESHOLD relaxes 0.5→0.45 (single analysis quality since depth-tier removal)",
    )

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
    batch_douyin_videos_per_niche: int = Field(default=10, ge=1)

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
