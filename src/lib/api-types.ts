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

export type ScriptExportFormat = "copy" | "pdf";

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
}

export interface CalendarSlotData {
  day_idx: number;           // 0 = Thứ 2 … 6 = Chủ nhật
  day: string;               // "Thứ 4" (pre-formatted VN)
  suggested_time: string;    // "20:00"
  kind: "pattern" | "ideas" | "timing" | "repost";
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

export type ReportV1 =
  | { kind: "pattern"; report: PatternReportPayload }
  | { kind: "ideas"; report: IdeasReportPayload }
  | { kind: "timing"; report: TimingReportPayload }
  | { kind: "lifecycle"; report: LifecycleReportPayload }
  | { kind: "generic"; report: GenericReportPayload };

/** §J names — same shapes as `*ReportPayload` (plan uses `PatternPayload`, …). */
export type PatternPayload = PatternReportPayload;
export type IdeasPayload = IdeasReportPayload;
export type TimingPayload = TimingReportPayload;
export type LifecyclePayload = LifecycleReportPayload;
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
