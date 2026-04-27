/**
 * Phase B — Cloud Run + SPA shared contracts (`artifacts/plans/phase-b-plan.md`).
 * Extend here before wiring routes or Python response models.
 */

import type { CommentRadarData, ThumbnailAnalysisData } from "@/lib/types/corpus-sidecars";

// ---------------------------------------------------------------------------
// B.1 — POST /video/analyze (and Supabase `video_diagnostics` row)
// ---------------------------------------------------------------------------

export type VideoAnalyzeMode = "win" | "flop";

export type RetentionCurveSource = "real" | "modeled";

/** Core meta; field names align with plan JSON + fixture mapping. */
export interface VideoAnalyzeMeta {
  creator: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  save_rate: number;
  duration_sec: number;
  thumbnail_url: string | null;
  date_posted: string | null;
  /** Fixture / UI: video title */
  title?: string;
  /** ``niche_taxonomy.name_vn`` / ``name_en`` — win report kicker ``BÁO CÁO PHÂN TÍCH · …``. */
  niche_label?: string;
  is_breakout?: boolean;
  saves?: number;
  /** Drives retention chart kicker (B.0.1): modeled vs real telemetry. */
  retention_source?: RetentionCurveSource;
}

export interface VideoKpi {
  label: string;
  value: string;
  delta: string;
  /** Optional Tailwind classes for the delta line (e.g. negative MoM). */
  deltaClassName?: string;
}

export interface VideoSegment {
  name: string;
  pct: number;
  color_key: string;
}

export interface VideoHookPhase {
  t_range: string;
  label: string;
  body: string;
}

export interface VideoLesson {
  title: string;
  body: string;
}

export type FlopIssueSeverity = "high" | "mid" | "low";

/** Flop-mode ``analysis_headline`` — five segments for serif/accent layout (JSON in DB). */
export interface FlopHeadline {
  prefix: string;
  view_accent: string;
  middle: string;
  prediction_pos: string;
  suffix: string;
}

export interface VideoFlopIssue {
  sev: FlopIssueSeverity;
  t: number;
  end: number;
  title: string;
  detail: string;
  fix: string;
}

export interface RetentionPoint {
  t: number;
  pct: number;
}

export interface VideoNicheMeta {
  avg_views: number;
  avg_retention: number;
  avg_ctr: number;
  sample_size: number;
  /** Corpus “winner” pool in niche (breakout ≥1.5 or ER > median_er); null if not computed. */
  winners_sample_size: number | null;
}

/** GET `/video/niche-benchmark` (Cloud Run, JWT). */
export interface VideoNicheBenchmarkResponse {
  niche_id: number;
  niche_meta: VideoNicheMeta | null;
  niche_benchmark_curve: RetentionPoint[];
  retention_source: RetentionCurveSource;
  computed_at: string | null;
  reference_duration_sec: number;
}

/** Response body for `POST /video/analyze`. */
export interface VideoAnalyzeResponse {
  video_id: string;
  mode: VideoAnalyzeMode;
  meta: VideoAnalyzeMeta;
  kpis: VideoKpi[];
  segments: VideoSegment[];
  hook_phases: VideoHookPhase[];
  lessons: VideoLesson[];
  /** Win: plain string. Flop: structured segments or legacy plain string. */
  analysis_headline: string | FlopHeadline | null;
  analysis_subtext: string | null;
  flop_issues: VideoFlopIssue[] | null;
  retention_curve: RetentionPoint[] | null;
  niche_benchmark_curve: RetentionPoint[] | null;
  niche_meta: VideoNicheMeta | null;
  /** Flop summary bar; deterministic client may also recompute. */
  projected_views?: number | null;
  /** Corpus thumbnail_analysis (Gemini on t=0 frame); null when unavailable. */
  thumbnail_analysis?: ThumbnailAnalysisData | null;
  /** Comment sentiment + purchase intent; null when sparse / fetch miss. */
  comment_radar?: CommentRadarData | null;
}

export type { CommentRadarData, ThumbnailAnalysisData } from "@/lib/types/corpus-sidecars";

// ── Wave 4 PR #3 — Compare flow stream payload ──────────────────────────
//
// Mirror of ``ComparePayload`` in
// ``cloud-run/getviews_pipeline/report_compare.py``. The /stream endpoint
// emits this as ``finalPayload`` when intent_type === "compare_videos".
//
// ``left`` and ``right`` carry the run_video_diagnosis output dicts —
// typed minimally here because CompareBody only reads a handful of
// fields (creator handle, hook_type, scene count, breakout, views).
// We intentionally keep the type structural rather than mirroring every
// field on the server side; expand only when the FE needs more.

export interface VideoDiagnosisStreamSide {
  intent?: "video_diagnosis";
  niche?: string;
  metadata?: {
    video_id?: string;
    duration_sec?: number;
    engagement_rate?: number | null;
    /** ``views / creator avg``. Server may set ``breakout`` or
     * ``breakout_multiplier``; the FE reads either. */
    breakout?: number | null;
    breakout_multiplier?: number | null;
    metrics?: {
      views?: number | null;
      likes?: number | null;
      comments?: number | null;
      shares?: number | null;
      bookmarks?: number | null;
    };
    author?: {
      username?: string;
      display_name?: string;
      followers?: number | null;
    };
    thumbnail_url?: string | null;
    tiktok_url?: string | null;
  };
  analysis?: {
    transitions_per_second?: number | null;
    scenes?: Array<Record<string, unknown>>;
    hook_analysis?: {
      hook_type?: string | null;
      hook_phrase?: string | null;
      face_appears_at?: number | null;
    };
  };
  diagnosis?: string;
  /** Wave 3 — Layer 0 execution_tip surfaced on the diagnosis payload. */
  niche_execution_tip?: string | null;
  thumbnail_analysis?: ThumbnailAnalysisData | null;
  comment_radar?: CommentRadarData | null;
}

export type CompareHookAlignment = "match" | "conflict" | "unknown";
export type CompareHigherSide = "left" | "right" | "tie" | "unknown";

export interface CompareDelta {
  /** 1-2 sentence VN summary, voice_lint-clean. */
  verdict: string;
  hook_alignment: CompareHookAlignment;
  higher_breakout_side: CompareHigherSide;
  /** ``left - right`` orientation; null when either side lacks the metric. */
  breakout_gap?: number | null;
  scene_count_diff?: number | null;
  transitions_per_second_diff?: number | null;
  left_hook_type?: string | null;
  right_hook_type?: string | null;
  /** True when the verdict is the deterministic templated fallback
   *  (Gemini failed or its output tripped voice_lint). FE may render
   *  a subtle muted indicator; not user-blocking. */
  verdict_fallback?: boolean;
}

export interface ComparePayload {
  intent: "compare_videos";
  niche?: string | null;
  left: VideoDiagnosisStreamSide;
  right: VideoDiagnosisStreamSide;
  delta: CompareDelta;
}

/** Row shape for `public.video_diagnostics` (no `mode` — join corpus for mode). */
export interface VideoDiagnosticsRow {
  video_id: string;
  analysis_headline: string | null;
  analysis_subtext: string | null;
  lessons: VideoLesson[];
  hook_phases: VideoHookPhase[];
  segments: VideoSegment[];
  flop_issues: VideoFlopIssue[] | null;
  retention_curve: RetentionPoint[] | null;
  niche_benchmark_curve: RetentionPoint[] | null;
  computed_at: string;
}

// ---------------------------------------------------------------------------
// B.3 — GET /channel/analyze
// ---------------------------------------------------------------------------

export type ChannelFormulaGate = "thin_corpus" | null;

export interface ChannelFormulaStep {
  step: string;
  detail: string;
  pct: number;
}

export interface ChannelLesson {
  title: string;
  body: string;
}

/**
 * PR-3 Studio Home — typed cadence shape backing the design's NHỊP ĐĂNG block.
 *
 * Source of truth:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::_compute_cadence_struct``.
 */
export interface ChannelCadence {
  /**
   * Exactly 14 entries; ``[0]`` = today − 13, ``[13]`` = today.
   * Each cell is whether the kênh posted at least once on that day.
   */
  posts_14d: boolean[];
  /** Posts in the trailing 7 days. */
  weekly_actual: number;
  /** Cap-7 target derived from rolling 30-day unique-days-with-post; always ≥ ``weekly_actual``. */
  weekly_target: number;
  /** "20:00–22:00" 2-hour window centred on the peak hour; "" if unknown. */
  best_hour: string;
  /** Vietnamese short labels comma-separated, e.g. "T7, CN". "" if unknown. */
  best_days: string;
}

/**
 * PR-2 Studio Home — diagnostic items.
 *
 * The design pack's MyChannelCard §C/§D restructures the kênh's lessons
 * into typed strengths (TẬN DỤNG) + weaknesses (CÁCH SỬA). Each item
 * carries a metric line for quantified evidence and an optional bridge
 * pointing to a tier in the design's "GỢI Ý HÔM NAY" stack:
 *   • "01" — Quay ngay (script + kịch bản)
 *   • "02" — Pattern dễ remix
 *
 * Source of truth:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::ChannelStrengthLLM``.
 */
export interface ChannelDiagnosticItem {
  title: string;
  metric: string;
  why: string;
  action: string;
  /** ``null`` when no clean tier to bridge to (e.g. legacy cached row). */
  bridge_to: "01" | "02" | null;
}

export interface ChannelTopVideo {
  video_id: string;
  title: string;
  views: number;
  thumbnail_url: string | null;
  bg_color?: string | null;
}

export interface ChannelKpiCell {
  label: string;
  value: string;
  delta: string;
}

/**
 * Per-niche channel-level percentiles powering the HomeMyChannelSection
 * benchmark layer. Source: SQL RPC ``niche_channel_benchmarks(p_niche_id)``
 * (migration ``20260528000000``) called from
 * ``cloud-run/getviews_pipeline/channel_analyze.py`` and folded into the
 * ``/channel/analyze`` response.
 *
 * ``channel_count`` is the sample size — per-creator aggregates over the
 * 30d corpus window with HAVING COUNT(*) >= 3 (excludes one-shot
 * creators whose single virality wave would skew the medians). When
 * ``channel_count = 0`` the FE should suppress the benchmark layer
 * entirely; the percentile fields are zeroed via SQL COALESCE in that
 * case so they remain numeric.
 *
 * ``engagement_*`` is on the same scale as ``ChannelAnalyzeResponse.
 * engagement_pct`` from the same niche slice — i.e. percent-form
 * (0..100) per how ``video_corpus.engagement_rate`` is stored.
 */
export interface NicheChannelBenchmarks {
  channel_count: number;
  avg_views_p50: number;
  avg_views_p75: number;
  engagement_p50: number;
  engagement_p75: number;
  posts_per_week_p50: number;
  posts_per_week_p75: number;
}

/**
 * Studio Home pulse hero (PR-1) — streak chip + serif headline.
 *
 * Mirrors ``_compute_pulse`` in
 * ``cloud-run/getviews_pipeline/channel_analyze.py``. Headline is a
 * deterministically-templated Vietnamese sentence (no Gemini), so it's
 * present on cache-hit responses too.
 */
export interface ChannelPulse {
  streak_days: number;
  /** Window cap (always 14 today; reserved for future tuning). */
  streak_window: number;
  headline: string;
  headline_kind: "win" | "concern" | "neutral";
  /** Pre-formatted MoM delta string (e.g. "↑ 18% MoM" or "—"). */
  mom_delta: string;
  /** Channel average views — referenced when the FE shows a sub-line under the streak. */
  avg_views: number;
}

/** Studio Home recent-7d ranked verdict list (PR-1). */
export interface ChannelRecent7dEntry {
  video_id: string;
  title: string;
  thumbnail_url: string | null;
  /** Empty / null when ``video_corpus.hook_type`` was missing. */
  hook_category: string | null;
  /** ISO timestamp from ``video_corpus.posted_at`` (or ``created_at`` fallback). */
  posted_at: string | null;
  /** Vietnamese short form: "3 giờ trước" / "2 ngày trước" / "5 tuần trước". */
  age_label: string;
  views: number;
  /** Rounded ratio: ``views / max(channel_avg_views, 1)``. Float, 1.0 = on average. */
  vs_median: number;
  verdict: "WIN" | "AVG" | "UNDER";
  /** Heuristic Vietnamese template; no Gemini. */
  verdict_note: string;
}

export interface ChannelAnalyzeResponse {
  handle: string;
  niche_id: number;
  name: string;
  bio: string | null;
  followers: number;
  total_videos: number;
  avg_views: number;
  engagement_pct: number;
  posting_cadence: string | null;
  posting_time: string | null;
  top_hook: string | null;
  formula: ChannelFormulaStep[] | null;
  formula_gate: ChannelFormulaGate;
  lessons: ChannelLesson[];
  top_videos: ChannelTopVideo[];
  niche_label: string | null;
  kpis: ChannelKpiCell[];
  optimal_length?: string | null;
  /** ISO timestamp of cached row (``channel_formulas.computed_at``) or fresh run. */
  computed_at?: string | null;
  /** True when served from fresh ``channel_formulas`` row (< 7d) without Gemini. */
  cache_hit?: boolean;
  /**
   * D.1.4 — 7×8 video-count matrix keyed by (weekday=Mon..Sun, hour-bucket).
   * Empty array signals "insufficient temporal data" — hide the panel.
   */
  posting_heatmap?: number[][];
  /**
   * Per-niche channel-level percentiles for HomeMyChannelSection bars +
   * "Ngách: …" / "Top 25%: …" labels. Optional so older /channel/analyze
   * responses pre-RPC remain decodable.
   */
  niche_benchmarks?: NicheChannelBenchmarks;
  /**
   * Studio Home pulse hero (PR-1) — streak chip + headline. Optional
   * because pre-PR-1 cached responses won't carry it; FE hides the
   * block in that case.
   */
  pulse?: ChannelPulse;
  /**
   * Studio Home recent-7d ranked verdict list (PR-1). Empty array when
   * the kênh has no posts in the last 7 days; FE shows a thin "no
   * recent posts" stub instead of the rows.
   */
  recent_7d?: ChannelRecent7dEntry[];
  /**
   * PR-2 — diagnostic strengths block (TẬN DỤNG, ▲ ĐANG TỐT).
   * Empty array when the cached row predates PR-2 schema; FE hides the
   * strengths section in that case until the row's TTL expires and a
   * fresh Gemini run repopulates it.
   */
  strengths?: ChannelDiagnosticItem[];
  /**
   * PR-2 — diagnostic weaknesses block (CÁCH SỬA, ✕ CẦN CẢI THIỆN).
   * Same legacy-empty fallback as ``strengths``.
   */
  weaknesses?: ChannelDiagnosticItem[];
  /**
   * PR-3 — typed cadence (NHỊP ĐĂNG block).
   * ``null`` when the BE didn't have enough temporal data; FE hides
   * the cadence section in that case.
   */
  cadence?: ChannelCadence | null;
}

// ---------------------------------------------------------------------------
// B.4 — POST /script/generate, GET hook-patterns, GET scene-intelligence
// ---------------------------------------------------------------------------

export type ScriptTone =
  | "Hài"
  | "Chuyên gia"
  | "Tâm sự"
  | "Năng lượng"
  | "Mỉa mai";

export interface ScriptGenerateRequest {
  topic: string;
  hook: string;
  hook_delay_ms: number;
  duration: number;
  tone: ScriptTone;
  niche_id: number;
}

export interface ScriptShot {
  t0: number;
  t1: number;
  cam: string;
  voice: string;
  viz: string;
  overlay: string;
  corpus_avg?: number;
  winner_avg?: number;
  /** Join key for ``scene_intelligence`` merge on the client. */
  intel_scene_type?: string;
  overlay_winner?: string;
  /**
   * Wave 2.5 Phase B PR #6 — per-shot enrichment dimensions emitted by
   * Gemini (or filled from the deterministic backbone). Present on newly
   * generated shots; may be missing on pre-PR #6 cached drafts.
   */
  framing?: string | null;
  pace?: string | null;
  overlay_style?: string | null;
  subject?: string | null;
  motion?: string | null;
  /**
   * Wave 2.5 Phase B PR #7 — up to 3 real creator scenes matching this
   * shot, surfaced in the studio as reference cards. Empty array (or
   * missing) on old drafts / matcher failure.
   */
  references?: ShotReference[];
}

/**
 * One matched reference from the ``video_shots`` corpus — feeds the
 * reference-card strip under each shot. Shape mirrors the server's
 * ``ShotReference.to_dict()`` in ``shot_reference_matcher.py``.
 */
export interface ShotReference {
  video_id: string;
  scene_index: number;
  start_s: number | null;
  end_s: number | null;
  frame_url: string | null;
  thumbnail_url: string | null;
  tiktok_url: string | null;
  creator_handle: string | null;
  description: string | null;
  /**
   * Denormalized from ``video_corpus.views`` at write time — drives the
   * "256K view" credibility pill on each RefClipCard. NULL on rows that
   * predate the ``20260601000000_video_shots_views`` migration's backfill
   * window; FE branches on null and just hides the pill.
   */
  views: number | null;
  score: number;
  /** Internal keys used for scoring; FE shows ``match_label`` instead. */
  match_signals: string[];
  /** Human-readable VN chip, e.g. ``"Cùng ngách, hook, khung hình"``. */
  match_label: string;
}

export interface ScriptGenerateResponse {
  shots: ScriptShot[];
}

// ---------------------------------------------------------------------------
// D.1.1 — POST /script/save + /script/drafts + export
// ---------------------------------------------------------------------------

export interface ScriptSaveRequest {
  topic: string;
  hook: string;
  hook_delay_ms: number;
  duration_sec: number;
  tone: ScriptTone;
  shots: ScriptShot[];
  niche_id?: number | null;
  source_session_id?: string | null;
}

export interface ScriptDraftRow {
  id: string;
  user_id?: string;
  topic: string;
  hook: string;
  hook_delay_ms: number;
  duration_sec: number;
  tone: ScriptTone;
  shots: ScriptShot[];
  niche_id?: number | null;
  source_session_id?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ScriptSaveResponse {
  draft_id: string;
  draft: ScriptDraftRow;
}

export interface ScriptDraftsListResponse {
  drafts: ScriptDraftRow[];
}

export interface ScriptDraftResponse {
  draft: ScriptDraftRow;
}

/**
 * Per design pack ``screens/script.jsx`` lines 838-857 the export modal
 * offers three user-facing formats. ``copy`` is a back-compat alias kept
 * for any caller still on the legacy clipboard-paste path.
 */
export type ScriptExportFormat = "shoot" | "markdown" | "plain" | "copy";

/**
 * B.4 — ``ForecastBar`` view/retention/hook-score math is **client-only** (no API).
 * Implementations: ``scriptForecastViews``, ``scriptForecastRetentionPct``, ``scriptHookScore``
 * in ``src/components/v2/ScriptForecastBar.tsx`` (used by ``/app/script``).
 */

export interface HookPatternRow {
  pattern: string;
  delta: string;
  uses: number;
  avg_views: number;
}

export interface HookPatternsResponse {
  niche_id: number;
  hook_patterns: HookPatternRow[];
  citation?: {
    sample_size: number;
    niche_label: string;
    window_days: number;
  };
}

/**
 * S3 — One row in the IdeaRefStrip above the script storyboard. Mirrors
 * the BE shape from ``fetch_idea_references_for_niche`` in
 * ``cloud-run/getviews_pipeline/script_data.py``. Used to render the
 * 5-card "5 video viral cùng angle" surface in /app/script per design
 * pack ``screens/script.jsx`` lines 1284-1360.
 */
export interface ScriptIdeaReference {
  video_id: string;
  creator_handle: string | null;
  tiktok_url: string | null;
  thumbnail_url: string | null;
  views: number;
  duration_sec: number | null;
  hook_type: string | null;
  /** Hook phrase or trimmed caption — what the ref shot is "about". */
  shot_label: string | null;
  /** 50–100. Niche match = 50 base + 30 hook bonus + up to 20 from views. */
  match_pct: number;
}

export interface ScriptIdeaReferencesResponse {
  niche_id: number;
  hook_type: string | null;
  references: ScriptIdeaReference[];
}

export interface SceneIntelligenceRow {
  niche_id: number;
  scene_type: string;
  corpus_avg_duration: number | null;
  winner_avg_duration: number | null;
  winner_overlay_style: string | null;
  overlay_samples: string[];
  tip: string | null;
  reference_video_ids: string[];
  sample_size: number;
  computed_at: string;
}

export interface SceneIntelligenceResponse {
  niche_id: number;
  scenes: SceneIntelligenceRow[];
}

export interface ScriptReferenceClip {
  video_id: string;
  thumbnail_url: string | null;
  handle: string;
  label: string;
  duration_sec: number;
}

// ---------------------------------------------------------------------------
// B.2 — GET /kol/browse, POST /kol/toggle-pin (Cloud Run)
// ---------------------------------------------------------------------------

export type KolBrowseTab = "pinned" | "discover";

export interface KolBrowseRow {
  handle: string;
  name: string;
  niche_label: string | null;
  followers: number;
  avg_views: number;
  growth_30d_pct: number;
  match_score: number;
  is_pinned: boolean;
  /** One-sentence rationale from Cloud Run (B.2.2 gap). */
  match_description?: string | null;
}

export interface KolBrowseResponse {
  tab: KolBrowseTab;
  niche_id: number;
  page: number;
  page_size: number;
  total: number;
  reference_handles: string[];
  rows: KolBrowseRow[];
}

// ---------------------------------------------------------------------------
// Phase C — §J ReportV1 + answer session (mirror `report_types.py`)
// ---------------------------------------------------------------------------

export interface ConfidenceStripData {
  sample_size: number;
  window_days: number;
  niche_scope: string | null;
  freshness_hours: number;
  intent_confidence: "high" | "medium" | "low";
  what_stalled_reason: string | null;
}

export interface MetricData {
  value: string;
  numeric: number;
  definition: string;
}

export interface LifecycleData {
  first_seen: string;
  peak: string;
  momentum: "rising" | "plateau" | "declining";
}

export interface ContrastAgainstData {
  pattern: string;
  why_this_won: string;
}

export interface HookFindingData {
  rank: number;
  pattern: string;
  retention: MetricData;
  delta: MetricData;
  uses: number;
  lifecycle: LifecycleData;
  contrast_against: ContrastAgainstData;
  prerequisites: string[];
  insight: string;
  evidence_video_ids: string[];
}

export interface SumStatData {
  label: string;
  value: string;
  trend: string;
  tone: "up" | "down" | "neutral";
}

export interface EvidenceCardPayloadData {
  video_id: string;
  creator_handle: string;
  title: string;
  views: number;
  retention: number;
  duration_sec: number;
  bg_color: string;
  hook_family: string;
  /** Cover URL when present (falls back to `bg_color` tile). */
  thumbnail_url?: string | null;
}

export interface PatternCellPayloadData {
  title: string;
  finding: string;
  detail: string;
  chart_kind: "duration" | "hook_timing" | "sound_mix" | "cta_bars";
  chart_data?: unknown;
}

export interface ActionCardPayloadData {
  icon: string;
  title: string;
  sub: string;
  cta: string;
  primary?: boolean | null;
  route?: string | null;
  forecast: Record<string, string>;
}

export interface SourceRowData {
  kind: "video" | "channel" | "creator" | "datapoint";
  label: string;
  count: number;
  sub: string;
}

export interface WoWDiffData {
  new_entries: Array<Record<string, unknown>>;
  dropped: Array<Record<string, unknown>>;
  rank_changes: Array<Record<string, unknown>>;
}

export interface PatternReportPayload {
  confidence: ConfidenceStripData;
  wow_diff: WoWDiffData | null;
  tldr: { thesis: string; callouts?: SumStatData[] };
  findings: HookFindingData[];
  what_stalled: HookFindingData[];
  evidence_videos: EvidenceCardPayloadData[];
  patterns: PatternCellPayloadData[];
  actions: ActionCardPayloadData[];
  sources: SourceRowData[];
  related_questions: string[];
  subreports?: Record<string, unknown> | null;
}

export interface IdeaBlockPayloadData {
  id: string;
  title: string;
  tag: string;
  angle: string;
  why_works: string;
  evidence_video_ids: string[];
  hook: string;
  slides: Array<Record<string, unknown>>;
  metric: Record<string, string>;
  prerequisites: string[];
  confidence: Record<string, number>;
  style: string;
  // 2026-05-10 — Wave 2 PR #2/#3: "5 video tiếp theo" content-calendar fields.
  // All optional for back-compat; older payloads render unchanged.
  rank?: number;                                              // 1..5
  opening_line?: string;                                      // 6-12 word VN first-spoken-line
  lifecycle_stage?: "early" | "peak" | "decline" | null;
}

/** 2026-05-10 — Wave 2 PR #1: Layer 0 niche_insights injection.
 * Shared by PatternPayload + IdeasPayload so the "what to do next"
 * slot can surface `execution_tip` in either report. */
export interface NicheInsightData {
  insight_text: string | null;
  execution_tip: string | null;
  top_formula_hook: string | null;
  top_formula_format: string | null;
  week_of: string | null;                                      // YYYY-MM-DD
  staleness_risk: "LOW" | "MODERATE" | "HIGH" | null;
}

export interface IdeasReportPayload {
  confidence: ConfidenceStripData;
  lead: string;
  ideas: IdeaBlockPayloadData[];
  style_cards: Array<Record<string, unknown>>;
  stop_doing: Array<Record<string, string>>;
  actions: ActionCardPayloadData[];
  sources: SourceRowData[];
  related_questions: string[];
  variant: "standard" | "hook_variants";
  niche_insight?: NicheInsightData | null;
}

/** Named alias for ``CalendarSlotData.kind`` — intentionally distinct
 * from ``ReportV1["kind"]`` even though the two share some literal values.
 * Mirrors ``CalendarSlotKind`` in ``cloud-run/getviews_pipeline/
 * report_types.py``. Don't substitute either where the other is
 * expected — the narrower slot-kind domain includes ``"repost"``, and
 * the report envelope kind includes ``"generic" | "lifecycle" |
 * "diagnostic"``.
 */
export type CalendarSlotKindData = "pattern" | "ideas" | "timing" | "repost";

export interface CalendarSlotData {
  day_idx: number;           // 0 = Thứ 2 … 6 = Chủ nhật
  day: string;               // "Thứ 4" (pre-formatted VN)
  suggested_time: string;    // "20:00"
  kind: CalendarSlotKindData;
  title: string;
  rationale: string;
}

export interface TimingReportPayload {
  confidence: ConfidenceStripData;
  top_window: Record<string, unknown>;
  top_3_windows: Array<Record<string, unknown>>;
  lowest_window: Record<string, string>;
  grid: number[][];
  variance_note: Record<string, string>;
  fatigue_band: Record<string, unknown> | null;
  /** Content calendar slots — absorbs the ``content_calendar`` intent
   *  into Timing. Empty means "pure timing query" (heatmap only);
   *  non-empty renders the 7-day strip. */
  calendar_slots: CalendarSlotData[];
  actions: ActionCardPayloadData[];
  sources: SourceRowData[];
  related_questions: string[];
}

export interface GenericReportPayload {
  confidence: ConfidenceStripData;
  off_taxonomy: Record<string, unknown>;
  narrative: Record<string, unknown>;
  evidence_videos: EvidenceCardPayloadData[];
  sources: SourceRowData[];
  related_questions: string[];
}

// ── Lifecycle template (2026-04-22) ────────────────────────────────────────
// Serves ``format_lifecycle_optimize`` / ``fatigue`` / ``subniche_breakdown``
// intents. ``mode`` discriminator drives the header copy + which optional
// cell field (retention_pct vs instance_count) the body surfaces.

export type LifecycleModeData = "format" | "hook_fatigue" | "subniche";
export type LifecycleStageData = "rising" | "peak" | "plateau" | "declining";

export interface LifecycleCellData {
  name: string;
  stage: LifecycleStageData;
  /** Week-over-week reach delta, percent. Can be negative. */
  reach_delta_pct: number;
  /** 0-100 composite score (delta + lift vs niche median). */
  health_score: number;
  /** Format mode only — retention percent. Null in hook_fatigue / subniche. */
  retention_pct: number | null;
  /** Subniche mode only — creator count in this sub-niche. Null elsewhere. */
  instance_count: number | null;
  /** Query-aware Vietnamese insight, ≤240 chars. */
  insight: string;
}

export interface RefreshMoveData {
  title: string;
  detail: string;
  effort: "low" | "medium" | "high";
}

export interface LifecycleReportPayload {
  confidence: ConfidenceStripData;
  mode: LifecycleModeData;
  /** 1-sentence subject line, ≤240 chars. */
  subject_line: string;
  cells: LifecycleCellData[];
  /** Pydantic invariant: only populated when at least one cell is weak
   * (``declining`` or ``plateau``). An empty list is always valid. */
  refresh_moves: RefreshMoveData[];
  actions: ActionCardPayloadData[];
  sources: SourceRowData[];
  related_questions: string[];
}

// ── Diagnostic template (2026-04-22) ──────────────────────────────────────
// Serves ``own_flop_no_url`` — URL-less flop diagnosis with a 4-level
// verdict enum instead of a numeric score (we don't have the video).

export type DiagnosticVerdictData =
  | "likely_issue"
  | "possible_issue"
  | "unclear"
  | "probably_fine";

export interface DiagnosticCategoryData {
  name: string;
  verdict: DiagnosticVerdictData;
  finding: string;
  /** Absent when verdict is ``probably_fine`` (Pydantic invariant). */
  fix_preview: string | null;
}

export interface DiagnosticPrescriptionData {
  priority: "P1" | "P2" | "P3";
  action: string;
  impact: string;
  effort: "low" | "medium" | "high";
}

export interface DiagnosticReportPayload {
  confidence: ConfidenceStripData;
  /** 1-sentence framing — must acknowledge the no-URL constraint. */
  framing: string;
  /** Exactly 5 categories, position-pinned to Hook / Pacing / CTA /
   *  Sound / Caption & Hashtag. */
  categories: DiagnosticCategoryData[];
  /** 1-3 ranked fixes. Always non-empty — at minimum the paste-link nudge. */
  prescriptions: DiagnosticPrescriptionData[];
  /** CTA pointing back to /app/video for exact scoring. */
  paste_link_cta: { title: string; route: string };
  sources: SourceRowData[];
  related_questions: string[];
  /**
   * Wave 3 — the current week's Layer 0 execution_tip for this niche
   * (from ``niche_insights.execution_tip``). Rendered as a distinct
   * callout inside the "Ưu tiên sửa" section when present. Null when
   * Layer 0 hasn't run yet / the niche is sparse — render-time guard
   * in DiagnosticBody hides the surface. Max 240 chars (server-side).
   */
  niche_execution_tip?: string | null;
}

export type ReportV1 =
  | { kind: "pattern"; report: PatternReportPayload }
  | { kind: "ideas"; report: IdeasReportPayload }
  | { kind: "timing"; report: TimingReportPayload }
  | { kind: "lifecycle"; report: LifecycleReportPayload }
  | { kind: "diagnostic"; report: DiagnosticReportPayload }
  | { kind: "generic"; report: GenericReportPayload };

/** §J names — same shapes as `*ReportPayload` (plan uses `PatternPayload`, …). */
export type PatternPayload = PatternReportPayload;
export type IdeasPayload = IdeasReportPayload;
export type TimingPayload = TimingReportPayload;
export type LifecyclePayload = LifecycleReportPayload;
export type DiagnosticPayload = DiagnosticReportPayload;
export type GenericPayload = GenericReportPayload;

export interface AnswerSessionRow {
  id: string;
  user_id: string;
  title: string | null;
  initial_q: string;
  intent_type: string;
  format: "pattern" | "ideas" | "timing" | "generic" | "lifecycle" | "diagnostic";
  niche_id: number | null;
  created_at?: string;
  updated_at?: string;
  archived_at?: string | null;
}

export interface AnswerTurnRow {
  id: string;
  session_id: string;
  turn_index: number;
  kind: string;
  query: string;
  payload: ReportV1;
  credits_used?: number;
  classifier_confidence?: "high" | "medium" | "low";
  intent_confidence?: "high" | "medium" | "low";
  cloud_run_run_id?: string | null;
  created_at?: string;
}

/** §J — plan naming (`AnswerSession` / `AnswerTurn`); same shapes as `*Row` from Supabase. */
export type AnswerSession = AnswerSessionRow;
export type AnswerTurn = AnswerTurnRow;
