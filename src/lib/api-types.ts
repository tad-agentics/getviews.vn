/**
 * Phase B — Cloud Run + SPA shared contracts (`artifacts/plans/phase-b-plan.md`).
 * Extend here before wiring routes or Python response models.
 */

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
}

export interface ScriptGenerateResponse {
  shots: ScriptShot[];
}

export interface HookPatternRow {
  pattern: string;
  delta: string;
  uses: number;
  avg_views: number;
}

export interface HookPatternsResponse {
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
  tone: string;
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
