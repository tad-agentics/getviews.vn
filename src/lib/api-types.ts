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
  /** Ratio (0–1), matches ``video_corpus.save_rate`` storage. The KPI
   * strip renders it as a percent (``build_kpis`` × 100); ``meta.save_rate``
   * itself stays in ratio space so cross-cohort math
   * (e.g. % vs niche.median) stays self-consistent. ``formatSaveRatePct``
   * in VideoBody defends against legacy rows that may have leaked a
   * percent value into this field. */
  save_rate: number;
  duration_sec: number;
  thumbnail_url: string | null;
  date_posted: string | null;
  /** Legacy display line — first line of TikTok ``desc``; prefer ``caption`` for overlay. */
  title?: string;
  /** Full TikTok post description (``aweme.desc``). */
  caption?: string | null;
  /** In-video hook / overlay phrase from Gemini extraction — not the post caption. */
  hook_phrase?: string | null;
  /** ``niche_taxonomy.name_vn`` / ``name_en`` — win report kicker ``BÁO CÁO PHÂN TÍCH · …``. */
  niche_label?: string;
  is_breakout?: boolean;
  saves?: number;
  /** Drives retention chart kicker (B.0.1): modeled vs real telemetry. */
  retention_source?: RetentionCurveSource;
  /** Channel-relative breakout — the creator's own median views over recent
   * posts. Distinct from {@link CreatorComparison.delta} (hit / flop within
   * the same channel). Renders the "X.Y× kênh trung bình" tag in the meta
   * strip. Null when the row predates `creator_median_views` ingest, or
   * when on-demand analysis has no historical-posts fetch. */
  creator_median_views?: number | null;
  /** ``views / creator_median_views`` rounded to 2dp. Pre-computed BE-side
   * so FE doesn't re-derive on every render. */
  target_vs_creator_median?: number | null;
  /** Engagement rate from corpus / TikTok metadata — powers bright-spot signal. */
  engagement_rate?: number;
  /** Legacy niche taxonomy id for corpus joins (format benchmarks, examples). */
  niche_id?: number;
  /** Canonical content format slug (e.g. "talking_head", "voiceover_b_roll").
   * Present on v5 responses; undefined on older corpus rows. */
  content_format?: string | null;
  /** Re-uploaded foreign footage with Vietnamese subtitles/dub (not native creator content). */
  foreign_reup?: boolean | null;
  /** §4.7 M4 — time-series snapshots (t0 / t6h / t24h) when corpus refetch ran. */
  stats_history?: StatsHistorySnapshot[] | null;
  /** Derived from ``stats_history`` — ``spike_then_flat`` when M4 criteria match. */
  distribution_shape?: "spike_then_flat" | string | null;
  /** Batch M1 ingest heuristic — ``organic_confident`` | ``suspect_low`` | ``suspect_medium`` | ``unknown``. */
  boost_attribution?: BoostAttributionLevel | string | null;
  /** False when ``boost_attribution`` is ``suspect_medium`` (excluded from ref pool). */
  reference_eligible?: boolean | null;
}

export type BoostAttributionLevel =
  | "unknown"
  | "organic_confident"
  | "suspect_low"
  | "suspect_medium";

/** One row in ``video_corpus.stats_history`` (M4 cron). */
export interface StatsHistorySnapshot {
  at: string;
  phase: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

/** Gemini hook micro-events in the opening 0–3s window. */
export type HookTimelineEventType =
  | "face_enter"
  | "first_word"
  | "text_overlay"
  | "sound_drop"
  | "cut"
  | "product_enter"
  | "reveal";

export interface HookTimelineEvent {
  t: number;
  event: HookTimelineEventType;
  note?: string;
}

/** One slide row from ``CarouselAnalysis.slides[]`` (ME-19 utilization). */
export interface CarouselSlideIntel {
  index: number;
  text_preview?: string | null;
  has_face?: boolean | null;
  has_product?: boolean | null;
  word_count?: number | null;
  text_density?: string | null;
  swipe_anchor?: string | null;
  layout?: string | null;
}

/** Carousel-level extraction surfaced on video diagnosis (§5.4). */
export interface CarouselIntelPayload {
  swipe_trigger_type?: string | null;
  has_numbered_hook?: boolean | null;
  content_arc?: string | null;
  visual_consistency?: string | null;
  estimated_read_time_seconds?: number | null;
  slide_pacing_score?: number | null;
  slides?: CarouselSlideIntel[];
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
  /** Optional; server may omit after hook phases became structural-only. */
  body?: string;
}

export interface VideoLesson {
  title: string;
  body: string;
}

export type FlopIssueSeverity = "high" | "mid" | "low";

export interface VideoFlopIssue {
  /** Stable id for narrative join (`loi_chinh_narrative[].error_id`); optional on legacy rows. */
  error_id?: string;
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
  /** Null / omitted when cohort has no positive benchmark (avoid showing "0"). */
  avg_views: number | null;
  avg_retention: number;
  avg_ctr: number;
  sample_size: number;
  /** Corpus “winner” pool in niche (breakout ≥1.5 or ER > median_er); null if not computed. */
  winners_sample_size: number | null;
  /**
   * Two-axis A.2.3 — which axis the benchmark cohort came from. Lets the FE
   * label "based on N similar-format videos" (sharper) vs "based on N videos
   * in your niche" (broader fallback). Optional because pre-A.2.3 API
   * responses didn't carry this; default to ``"niche"`` semantics in the FE.
   */
  benchmark_axis?: "content_class" | "niche" | "none";
  /** Optional BE cohort label (e.g. content class display name). */
  cohort_label?: string | null;
  /** Phase 2 — peer percentile within content_class cohort (when BE computes). */
  peer_percentile?: number | null;
  /** Human label e.g. "top 25% trong class". */
  peer_percentile_label?: string | null;
  avg_engagement_rate?: number;
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
/**
 * A.1 — cross-niche format signal.
 *
 * When the user's video has a recognised ``content_class_id``, the BE
 * looks at how the same ``format_axis`` (e.g. "pov_storytelling",
 * "tutorial", "review_unboxing") is performing across other niches in
 * the last 30 days. This surfaces "your format is rising in 5 niches —
 * here are the top hooks others are using" type insight that the
 * niche-only diagnosis can't see.
 *
 * Returned only when ``niches_with_format >= 3`` (cross-niche
 * meaningful) AND ``sample_size >= 20`` total — below that it's not
 * a "trend", it's noise.
 */
export interface CrossFormatHook {
  hook_type: string;
  hook_type_vi?: string;
  avg_views: number;
  niche_spread: number;
}

export interface CrossFormatSignal {
  format_axis: string;
  format_label_vi: string;
  niches_with_format: number;
  total_sample_size: number;
  top_hooks: CrossFormatHook[];
}

/** Same-creator hit vs flop comparison (video diagnosis). */
export interface CreatorComparisonVideo {
  video_id?: string | null;
  tiktok_url?: string | null;
  views: number;
  /** Caption excerpt from channel fetch (≤60 chars); not a hook taxonomy id. */
  hook_type?: string | null;
  thumbnail_url?: string | null;
}

export interface CreatorComparison {
  creator_handle: string;
  total_posts_analyzed: number;
  median_views: number;
  hit: CreatorComparisonVideo;
  flop: CreatorComparisonVideo;
  delta: number;
  target_vs_median: number;
  target_percentile: string;
}

/** Gemini-extracted creative context surfaced from `analysis_json`
 * (corpus path) or fresh on-demand extraction. Shape mirrors
 * `VideoEnrichmentPayload` in `cloud-run/getviews_pipeline/report_types.py`.
 * Null when no signal is populated. */
export interface VideoEnrichment {
  target_audience?: string | null;
  pain_points: string[];
  promotion_type: "organic" | "brand_deal" | "affiliate" | "self_promotion";
  style_tags: string[];
  tone?:
    | "educational"
    | "entertaining"
    | "emotional"
    | "humorous"
    | "inspirational"
    | "urgent"
    | "conversational"
    | "authoritative"
    | null;
}

export interface VideoAnalyzeResponse {
  video_id: string;
  mode: VideoAnalyzeMode;
  meta: VideoAnalyzeMeta;
  kpis: VideoKpi[];
  segments: VideoSegment[];
  hook_phases: VideoHookPhase[];
  /** Opening 0–3s micro-events from Gemini extraction; empty on legacy rows. */
  hook_timeline?: HookTimelineEvent[];
  /** Structured error cards from Call 1 (`error_id` joins `narrative_vi.loi_chinh_narrative`). */
  errors: VideoFlopIssue[];
  /** Same as ``errors`` when both are present — avoids SSE empty-array shadowing. */
  structural_errors?: VideoFlopIssue[];
  retention_curve: RetentionPoint[] | null;
  niche_benchmark_curve: RetentionPoint[] | null;
  niche_meta: VideoNicheMeta | null;
  /** Corpus thumbnail_analysis (Gemini on t=0 frame); null when unavailable. */
  thumbnail_analysis?: ThumbnailAnalysisData | null;
  /** Comment sentiment + purchase intent; null when sparse / fetch miss. */
  comment_radar?: CommentRadarData | null;
  /** A.1 cross-niche format signal; null when niches_with_format < 3. */
  cross_format_signal?: CrossFormatSignal | null;
  /** Same-creator hit/flop benchmark; null when fetch or sample too small. */
  creator_comparison?: CreatorComparison | null;
  /** Gemini enrichment (audience / pain points / promotion / style); null
   * when no signal was extracted (very short or low-energy videos). */
  enrichment?: VideoEnrichment | null;
}

export type { CommentRadarData, ThumbnailAnalysisData } from "@/lib/types/corpus-sidecars";

// ── Wave 4 PR #3 — Compare flow stream payload ──────────────────────────
//
// Mirror of ``ComparePayload`` in
// ``cloud-run/getviews_pipeline/report_compare.py``. Answer turn ``kind=compare``
// emits this as ``ReportV1`` payload when session format is ``compare``.
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
  /**
   * S6 — when set, the response carries only the shot at this index so
   * the FE can splice it back into local state without disturbing the
   * other 5 shots. Validated server-side as ``0 <= shot_index <= 5``.
   */
  shot_index?: number;
}

/**
 * S5 — One structured voice-over line. Mirrors ``VoLine`` in
 * ``cloud-run/getviews_pipeline/script_generate.py``. ``text`` may carry
 * inline ``*stress*`` markers that ``FormattedVO`` highlights; ``cue``
 * is rendered as a ``CueChip`` next to the line when present.
 */
export interface VoLine {
  t: string;
  text: string;
  cue?: string | null;
}

export interface ScriptShot {
  t0: number;
  t1: number;
  cam: string;
  voice: string;
  /**
   * S5 — structured voice-over (timed lines + inline cues + ``*stress*``
   * markers). Optional for back-compat with old drafts; the FE falls
   * back to the flat ``voice`` string when missing.
   */
  vo?: VoLine[];
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
  /**
   * 2026-06-11 — one-line data-grounded rationale for the shot, citing
   * the evidence Gemini saw (winning hooks / reference rhythm). Null
   * when there was nothing to cite; missing on old drafts.
   */
  reason_vi?: string | null;
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

/**
 * 2026-06-11 — one proof behind the script's structure. ``hook_stat``
 * rows come from ``hook_effectiveness``; ``hook_line`` rows are verbatim
 * winning hooks from ``video_corpus``. Mirrors
 * ``_build_format_rationale`` in ``script_generate.py``.
 */
export interface ScriptFormatProof {
  kind: "hook_stat" | "hook_line";
  /** hook_stat fields */
  label_vi?: string;
  hook_type?: string;
  avg_views?: number;
  completion_pct?: number;
  sample_size?: number;
  /** hook_line fields */
  phrase?: string;
  handle?: string;
  views?: number;
}

/** Deterministic "why this structure" block rendered above the shot list. */
export interface ScriptFormatRationale {
  text_vi: string;
  proofs: ScriptFormatProof[];
}

export interface ScriptGenerateResponse {
  shots: ScriptShot[];
  /** Null/missing when the niche had no hook evidence. */
  format_rationale?: ScriptFormatRationale | null;
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
 * One row from ``GET /script/idea-references`` (Cloud Run). Mirrors
 * ``fetch_idea_references_for_niche`` in ``script_data.py``.
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
  /** Distinct creators in corpus window using this hook (pattern report). */
  creator_count?: number | null;
  /** VN cultural angle for this pattern (pattern narrative, optional). */
  cultural_framing?: string | null;
  /** Richer journalist-style narrative (≤500 chars). When present, replaces `insight` in the UI. */
  narrative?: string | null;
  /** Psychological/cultural mechanism explaining why this hook works (≤350 chars). */
  why_it_works?: string | null;
  /** Specific viral sub-format callout detected in corpus (≤220 chars). Null = none detected. */
  micro_pattern?: string | null;
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
  /** Breakout signal: DB `breakout_ratio` or interim `breakout_multiplier`. */
  breakout_ratio?: number | null;
  /** Raw decimal (e.g. 0.087 = 8.7% ER); multiply by 100 for display. */
  engagement_rate?: number | null;
  days_ago?: number | null;
  tiktok_url?: string | null;
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

export interface OutlierStory {
  creator_handle: string;
  views: number;
  breakout_ratio: number;
  hook_type: string;
  days_ago: number | null;
}

export interface ABPairVideo {
  video_id: string;
  tiktok_url: string | null;
  views: number;
  hook_type: string;
  days_ago: number | null;
}

export interface PatternABPair {
  creator_handle: string;
  hit: ABPairVideo;
  flop: ABPairVideo;
  delta: number;
  hook_contrast: string;
}

export interface PatternReportPayload {
  confidence: ConfidenceStripData;
  wow_diff: WoWDiffData | null;
  tldr: { thesis: string; callouts?: SumStatData[] };
  narrative_vi?: { headline_vi?: string } | null;
  findings: HookFindingData[];
  what_stalled: HookFindingData[];
  evidence_videos: EvidenceCardPayloadData[];
  patterns: PatternCellPayloadData[];
  actions: ActionCardPayloadData[];
  sources: SourceRowData[];
  related_questions: string[];
  subreports?: Record<string, unknown> | null;
  outlier_story?: OutlierStory | null;
  /** Cross-hook themes from narrative synthesis (pattern report). */
  cross_pattern_synthesis?: string[];
  ab_pair?: PatternABPair | null;
  /** Layer 0 niche insight (Wave-2 PR #1) — same shape used by IdeasPayload.
   * Mirrors `PatternPayload.niche_insight` in
   * `cloud-run/getviews_pipeline/report_types.py`. Rendered via
   * `<NicheInsightCard>`; null when the cron hasn't populated a row,
   * the row is quality-flagged, or it's older than the freshness window. */
  niche_insight?: NicheInsightData | null;
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
  // 2026-05-10 — Wave 2 PR #2/#3: "3 video tiếp theo" content-calendar fields (ideas stack).
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
  narrative_vi?: { headline_vi?: string } | null;
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
  narrative_vi?: { headline_vi?: string } | null;
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
  /** Present when variance is lift-sparse: timing is not a differentiator. */
  contrarian_note?: string | null;
}

export interface GenericReportPayload {
  confidence: ConfidenceStripData;
  narrative_vi?: { headline_vi?: string } | null;
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
  narrative_vi?: { headline_vi?: string } | null;
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

// ── Video diagnosis narrative rebuild (SSE + persisted `VideoReportPayload`) ─

/** Evidence narrative item for each error — join on `error_id` ↔ `VideoFlopIssue.error_id`. */
export interface LoidChinhNarrativeItem {
  error_id: string;
  narrative: string;
  evidence_aweme_id: string | null;
}

export interface NarrativeVi {
  /** One-sentence headline (≤20 words) — replaces legacy analysis_headline. */
  headline_vi?: string;
  ket_luan_nhanh: string;
  van_de_chinh: string;
  loi_chinh_narrative: LoidChinhNarrativeItem[];
  /** Win tier only (≤3). Empty for flop/average/unknown. */
  lessons?: { title: string; body: string }[];
  dinh_huong_chien_luoc: string;
  /** When diagnosis synthesis uses the section-pool JSON path (`GETVIEWS_DIAGNOSIS_SECTION_MODE=1`). */
  _schema_version?: "v5" | "v6" | string;
  /** Structured sections + anchors from Cloud Run v6 envelope. */
  diagnosis_vi?: DiagnosisViV6;
}

/** Stable video-diagnosis section ids (Sprint 9 pool; grows with sprints). */
export type VideoDiagnosisSectionId =
  | "diagnosis"
  | "compliance"
  | "hook_analysis"
  | "distribution"
  | "niche_pattern"
  | "douyin_origin"
  | "channel_pattern"
  | "commerce"
  | "metadata"
  | "editing"
  | "sound"
  | "persona"
  | "boost_attribution"
  | "script_structure"
  | "next_video";

/** One closing finding card inside a v6 section. */
/** Timestamp window in the ANALYZED clip that backs a finding (BE-clamped to [0, duration]). */
export interface FindingEvidenceRef {
  start_sec?: number;
  end_sec?: number;
  /** Short Vietnamese label for the moment, e.g. "mặt vào khung". */
  label_vi?: string;
}

export interface DiagnosisFinding {
  title_vi?: string;
  body_vi?: string;
  fix_vi?: string;
  /** Optional moment in the analyzed video proving this finding (strengths cite own clip, not peers). */
  evidence_ref?: FindingEvidenceRef | null;
}

/** One section inside `diagnosis_vi.sections` — mirrors channel `ChannelSection` shape loosely for LLM JSON. */
export interface DiagnosisSectionVi {
  section_id: VideoDiagnosisSectionId | string;
  title?: string;
  title_vi?: string;
  text?: string;
  text_vi?: string;
  findings?: DiagnosisFinding[];
  embedded_tiles?: unknown[];
  next_video?: Record<string, unknown> | null;
}

export interface DiagnosisEvidenceAnchorVi {
  signal_id?: string;
  section_id?: string;
  type?: string;
  quote?: string;
  location?: string | null;
}

/** v6 diagnosis JSON envelope nested under `narrative_vi`. */
export interface DiagnosisViV6 {
  headline_vi: string;
  sections: DiagnosisSectionVi[];
  evidence_anchors?: DiagnosisEvidenceAnchorVi[];
}

/**
 * Typed boundary between extraction core and diagnosis core (Phase 3.6).
 * Mirrors the Python ``ExtractionResult`` Pydantic model in models.py.
 * The FE does not directly consume this — it is an internal pipeline contract
 * exposed here so the schema-contract CI test can verify alignment.
 */
export interface ExtractionResult {
  video_id: string;
  content_type: "video" | "carousel";
  /** VideoMetadata: video_id, description, duration_sec, metrics, author, music, etc. */
  metadata: Record<string, unknown>;
  /** Raw Gemini frame analysis; null for carousels or on error. */
  analysis: Record<string, unknown> | null;
  /** Carousel-specific Gemini analysis; null for video content. */
  carousel_analysis: Record<string, unknown> | null;
  /** validate_transcript verdict. */
  transcript_quality: Record<string, unknown> | null;
  /** Entry-cost badge (tier + reasons string list). */
  entry_cost: Record<string, unknown> | null;
  /** Non-null when Gemini failed; downstream must check before using analysis. */
  error: string | null;
}

export interface BrightSpotSignal {
  signal_type:
    | "hook_only_problem"
    | "performing_well"
    | "hook_and_distribution"
    | "content_and_hook";
  message_vi: string;
}

/** Qualitative view upside ladder (flop diagnoses) — ranges only, no predicted view counts. */
export interface ViewScenario {
  focus_vi: string;
  outcome_vi: string;
}

export interface FormatCardExample {
  aweme_id: string;
  desc: string;
  play_count: number;
  creator_handle: string;
  tiktok_url: string;
}

export interface FormatCard {
  format_name_vi: string;
  mechanism_vi: string;
  /** Canonical slug matching ``video_corpus.content_format`` (optional if only VI labels). */
  content_format?: string | null;
  view_range: string;
  engagement_rate: string;
  example_hook_vi: string;
  evidence_aweme_id: string | null;
  /** Top corpus rows for this format + niche; hidden when &lt; 2 samples. */
  format_examples?: FormatCardExample[];
}

export interface ChannelContextVideo {
  aweme_id: string;
  desc: string | null;
  views: number | null;
  content_format: string | null;
  tiktok_url?: string;
}

export interface ChannelContext {
  available: boolean;
  reason?: string;
  top_videos?: ChannelContextVideo[];
  bottom_videos?: ChannelContextVideo[];
  best_performing_format?: string;
  sample_size?: number;
  median_views?: number;
  performance_tier?: string;
  /** v5 — per-format view aggregation from recent creator posts.
   * Keys are content_format slugs; values carry avg/median/min/max/n.
   * Null/absent when < 2 formats with n ≥ 3 each. */
  per_format_views?: Record<string, unknown> | null;
}

export interface ReferenceVideoCard {
  aweme_id: string;
  desc: string | null;
  hook_type: string | null;
  content_format: string | null;
  views: number | null;
  engagement_rate: number | null;
  author_handle: string | null;
  thumbnail_url: string | null;
  tiktok_url: string | null;
  /** R2-hosted MP4 from corpus ingest — present ⇒ inline playback; never an expiring CDN URL. */
  playback_url?: string | null;
  source: "corpus" | "live_search";
}

/** Partial payload streamed before final Vietnamese synthesis lands on `ReportV1`. */
export interface VideoAnswerPreSynthesisPayload {
  bright_spot_signal?: BrightSpotSignal;
  performance_tier?: string;
  tier_ratio?: number | null;
  tier_benchmark_n?: number | null;
  reference_videos?: ReferenceVideoCard[];
}

export interface VideoAnswerNarrativeReadyPayload {
  narrative_vi?: NarrativeVi;
  format_cards?: FormatCard[];
  errors?: VideoFlopIssue[];
  bright_spot_signal?: BrightSpotSignal;
  view_scenarios?: ViewScenario[];
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

/** Video diagnosis report — same shape as `VideoAnalyzeResponse`,
 *  used as a session format on the answer surface.
 *
 *  ``source`` flags whether the report came from a corpus row or a
 *  fresh on-demand analysis (set by `run_video_analyze_on_demand`).
 *
 *  ``sources`` + ``related_questions`` are part of every other
 *  ``ReportV1`` body so the answer-shell readers (AnswerScreen,
 *  RelatedQs) can pull them generically. Video
 *  reports populate them best-effort: ``sources`` typically empty
 *  (one-video diagnosis has no comparison cohort to cite), and
 *  ``related_questions`` carries follow-up prompts the FE composer
 *  might surface — both optional so older payloads still validate.
 */
export type VideoReportPayload = VideoAnalyzeResponse & {
  source?: "corpus" | "on_demand";
  sources?: SourceRowData[];
  related_questions?: string[];
  /** Carousel-only: internal enum key (e.g. "carousel_product_roundup") */
  carousel_subformat?: string;
  /** Carousel-only: Vietnamese display label (e.g. "So sánh") */
  carousel_subformat_label?: string;
  /** Carousel-only: number of slides in the post */
  carousel_slide_count?: number;
  /** Carousel-only: structured slide intel from ``analysis_json`` (§5.4). */
  carousel_intel?: CarouselIntelPayload | null;
  narrative_vi?: NarrativeVi;
  bright_spot_signal?: BrightSpotSignal;
  /** Flop-only qualitative upside ladder (hook → format rewrite). */
  view_scenarios?: ViewScenario[];
  format_cards?: FormatCard[];
  channel_context?: ChannelContext;
  reference_videos?: ReferenceVideoCard[];
  /** Account-refined tier when available: `hit` | `average` | `flop` | `early` | `unknown` */
  performance_tier?: string;
  /**
   * 2026-06-11 — views ÷ format corpus average, the number that *generates*
   * the tier. The chip renders this instead of a bare HIT/FLOP badge.
   * Missing on pre-rollout cached reports (chip falls back to word labels).
   */
  tier_ratio?: number | null;
  /** Corpus sample size behind the benchmark — gates the verdict chip when thin. */
  tier_benchmark_n?: number | null;
  /** §4.11.3 — echo billing tier on persisted video report. */
  analysis_depth?: "basic" | "deep";
  /** §4.6 — turn-1 handoff attribution (trends / composer / evidence / …). */
  source_entry?: "trends" | "trends_douyin" | "composer" | "evidence" | "intent_cta";
  /** §4.11.3 — deep-only sections available in manifest but not synthesized at basic depth. */
  locked_sections?: {
    section_id: string;
    title_vi: string;
    signal_count?: number;
    teaser_vi?: string;
  }[];
};

/** §J — 6-shot TikTok script (answer ``builder_fmt == "script"``). */
export interface ScriptVoLineData {
  t: number | string;
  text: string;
  cue?: string | null;
}

export interface ScriptShotReferenceData {
  video_id?: string;
  thumbnail_url?: string;
  corpus_avg?: number;
  winner_avg?: number;
  creator_handle?: string;
  breakout_multiplier?: number;
  [key: string]: unknown;
}

export interface ScriptShotCardData {
  t0?: number;
  t1?: number;
  cam?: string;
  voice?: string;
  viz?: string;
  overlay?: string;
  intel_scene_type?: string;
  vo?: ScriptVoLineData[];
  references?: ScriptShotReferenceData[];
  corpus_avg?: number;
  winner_avg?: number;
  reason_vi?: string | null;
  [key: string]: unknown;
}

export interface ScriptReportPayload {
  topic: string;
  hook: string;
  hook_delay_ms: number;
  duration: number;
  tone: string;
  niche_label: string;
  /** Wave 2 — narrative-first script report (`_schema_version: "script_v1"`). */
  narrative_vi?: Pick<
    NarrativeVi,
    "headline_vi" | "ket_luan_nhanh" | "_schema_version" | "diagnosis_vi"
  >;
  shots: ScriptShotCardData[];
  /** 2026-06-11 — deterministic "why this structure" proofs; null/missing on old reports. */
  format_rationale?: ScriptFormatRationale | null;
  sources: SourceRowData[];
  related_questions: string[];
}

export type ReportV1 =
  | { kind: "pattern"; report: PatternReportPayload }
  | { kind: "ideas"; report: IdeasReportPayload }
  | { kind: "timing"; report: TimingReportPayload }
  | { kind: "lifecycle"; report: LifecycleReportPayload }
  | { kind: "diagnostic"; report: DiagnosticReportPayload }
  | { kind: "generic"; report: GenericReportPayload }
  | { kind: "video"; report: VideoReportPayload }
  | { kind: "script"; report: ScriptReportPayload }
  | { kind: "compare"; report: ComparePayload };

/** §J names — same shapes as `*ReportPayload` (plan uses `PatternPayload`, …). */
export type PatternPayload = PatternReportPayload;
export type IdeasPayload = IdeasReportPayload;
export type TimingPayload = TimingReportPayload;
export type LifecyclePayload = LifecycleReportPayload;
export type DiagnosticPayload = DiagnosticReportPayload;
export type GenericPayload = GenericReportPayload;
export type VideoPayload = VideoReportPayload;
export type ScriptPayload = ScriptReportPayload;

export const ANSWER_SESSION_FORMATS = [
  "pattern",
  "ideas",
  "timing",
  "generic",
  "lifecycle",
  "diagnostic",
  "video",
  "script",
  "compare",
] as const;

export type AnswerSessionFormat = (typeof ANSWER_SESSION_FORMATS)[number];

export interface AnswerSessionRow {
  id: string;
  user_id: string;
  title: string | null;
  initial_q: string;
  intent_type: string;
  format: AnswerSessionFormat;
  niche_id: number | null;
  created_at?: string;
  updated_at?: string;
  archived_at?: string | null;
  /**
   * A2 — number of turns in this session (primary + follow-ups).
   * Surfaced by ``list_sessions`` for the drawer's "N lượt" chip.
   * ``undefined`` on rows from ``GET /answer/sessions/:id`` (single-row
   * fetcher doesn't run the count query); FE branches on null/0 and
   * hides the chip.
   */
  turn_count?: number;
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


// ───────────────────────────────────────────────────────────────────
// D4a (2026-06-04) — Kho Douyin · feed types.
//
// Mirrors the BE serializer in
// ``cloud-run/getviews_pipeline/douyin_data.py``. The /douyin/feed
// endpoint returns ``{niches, videos}`` in one round-trip; FE filters
// + sorts client-side.
// ───────────────────────────────────────────────────────────────────

/** Adapt-difficulty tier from the D3 Gemini synth. NULL on rows the
 *  synth cron hasn't reached yet — FE renders a "human review pending"
 *  caveat below the chip. */
export type DouyinAdaptLevel = "green" | "yellow" | "red";

/** Tag enum mirrors the design pack pills exactly. Drives the
 *  modal's NOTE VĂN HOÁ section colour-coding. */
export type DouyinTranslatorNoteTag =
  | "TỪ NGỮ"
  | "BỐI CẢNH"
  | "NHẠC NỀN"
  | "ĐẠO CỤ"
  | "KHÔNG LỜI"
  | "TITLE";

export interface DouyinTranslatorNote {
  tag: DouyinTranslatorNoteTag;
  note: string;
}

export interface DouyinNiche {
  id: number;
  slug: string;
  name_vn: string;
  name_zh: string;
  name_en: string;
}

export interface DouyinVideo {
  video_id: string;
  douyin_url: string | null;
  niche_id: number | null;
  /** Creator handle from Douyin (no leading @). */
  creator_handle: string | null;
  /** Display name (can differ from handle). */
  creator_name: string | null;
  thumbnail_url: string | null;
  video_url: string | null;
  /** Seconds, fractional allowed. */
  video_duration: number | null;
  views: number;
  likes: number;
  /** Douyin emphasises saves heavily — separate from likes for the
   *  modal's mini-stat grid. */
  saves: number;
  engagement_rate: number | null;
  posted_at: string | null;
  /** Raw Chinese caption from the aweme ``desc`` field. */
  title_zh: string | null;
  /** Vietnamese title (D2a translator or D3 synth, whichever ran later). */
  title_vi: string | null;
  /** ≤ 120-char gloss for the FE card subtitle band. */
  sub_vi: string | null;
  hashtags_zh: string[];
  /** D3 synth fields — null until the synth cron grades the row. */
  adapt_level: DouyinAdaptLevel | null;
  adapt_reason: string | null;
  eta_weeks_min: number | null;
  eta_weeks_max: number | null;
  cn_rise_pct: number | null;
  /** Empty array on rows the synth hasn't graded yet. */
  translator_notes: DouyinTranslatorNote[];
  synth_computed_at: string | null;
  /** ISO timestamp — drives the FE "X ngày trước" relative chip. */
  indexed_at: string | null;
}

export interface DouyinFeedResponse {
  niches: DouyinNiche[];
  videos: DouyinVideo[];
}


// ───────────────────────────────────────────────────────────────────
// D5d (2026-06-05) — Kho Douyin · weekly pattern signals types.
//
// Mirrors the BE serializer in
// ``cloud-run/getviews_pipeline/douyin_patterns_data.py``. The
// ``GET /douyin/patterns`` endpoint returns the most-recent week's 3
// pattern cards per active niche as a flat array ordered by
// (niche_id ASC, rank ASC). FE groups by ``niche_id`` to render the
// 3-up cards above the §II video grid.
// ───────────────────────────────────────────────────────────────────

export interface DouyinPattern {
  /** UUID — stable identity for React keys + future modal drilldown. */
  id: string;
  niche_id: number;
  /** ISO Monday 00:00 UTC of the synth week (DATE on the BE, e.g.
   *  "2026-06-01"). FE renders "Tuần " + week_of. */
  week_of: string;
  /** 1-based ordinal — synthesiser-determined signal strength. */
  rank: 1 | 2 | 3;
  name_vn: string;
  /** Optional Chinese phrasing — null when the pattern is format-only. */
  name_zh: string | null;
  /** Fill-in-the-blank VN hook template; always contains "___". */
  hook_template_vi: string;
  format_signal_vi: string;
  /** 2-5 corpus video_ids that anchor the pattern. FE may join back
   *  to ``DouyinVideo.video_id`` to render thumbnails. */
  sample_video_ids: string[];
  /** Mean ``cn_rise_pct`` across the sample. NULL when none of the
   *  sampled rows have a delta yet (Douyin's 2nd snapshot pending). */
  cn_rise_pct_avg: number | null;
  /** ISO timestamp of the synth run that wrote the row. */
  computed_at: string | null;
}

export interface DouyinPatternsResponse {
  patterns: DouyinPattern[];
}

// ── Phase 4.0 — v5 Channel-First Narrative contract ───────────────────────

export interface VideoDiagnosisV5MetricItem {
  /** Formatted value: "467", "81%", "0.64%", "0.0%" */
  value: string;
  /** Vietnamese label: "lượt xem" | "giữ chân" | "ER" | "save" */
  label: string;
  /** Cohort comparison tag: "top 5%" | "thấp 4.5×" | null */
  cohort_tag: string | null;
  tone: "default" | "warn" | "bad";
}

export interface VideoDiagnosisV5Header {
  handle: string;
  duration_s: number;
  posted_at: string;
  caption: string;
  metrics: VideoDiagnosisV5MetricItem[];
}

export interface VideoDiagnosisV5ChannelProof {
  handle: string;
  winner: { views_range: string; format_label: string };
  loser: { views_range: string; format_label: string };
  pattern_note: string;
}

export interface VideoDiagnosisV5Error {
  rank: 1 | 2 | 3;
  /** Maps from VideoFlopIssue.sev: high→critical, mid→major, low→minor */
  severity: "critical" | "major" | "minor";
  title: string;
  body: string;
  fix: string;
}

export interface VideoDiagnosisV5CrossFormatCard {
  format_name: string;
  description: string;
  stat: { label: string; value: string };
  example: string;
}

export interface VideoDiagnosisV5CrossFormatWinners {
  sample_size: number;
  window_days: number;
  cards: VideoDiagnosisV5CrossFormatCard[];
}

export interface VideoDiagnosisV5NextStep {
  bold_lead: string;
  detail: string;
}

/**
 * v5 Channel-First Narrative response shape (Phase 4.0).
 * Enforced by schema-contract CI test (test_schema_contract.py).
 * Mirrors the Python ``VideoDiagnosisV5`` Pydantic model in models.py.
 */
export interface VideoDiagnosisV5 {
  header: VideoDiagnosisV5Header;
  /** 3-sentence Vietnamese channel-first narrative lead. */
  van_de_chinh: string;
  /** null when ≥2 formats with n≥3 not met in channel_context.per_format_views */
  channel_proof: VideoDiagnosisV5ChannelProof | null;
  /** Max 3 errors, pre-sorted severity desc: critical → major → minor */
  errors: VideoDiagnosisV5Error[];
  cross_format_winners: VideoDiagnosisV5CrossFormatWinners;
  next_steps: VideoDiagnosisV5NextStep[];
  collapsibles: {
    hook_analysis: { label: string; payload: Record<string, unknown> };
    script_structure: { label: string; payload: Record<string, unknown> };
    full_context: { label: string; payload: Record<string, unknown> };
  };
}

// ---------------------------------------------------------------------------
// Channel Diagnosis — Lightreel-style narrative types (Layer 4a)
// ---------------------------------------------------------------------------

export type TrajectoryShape =
  | "decline_from_peak"
  | "stagnant"
  | "steady_growth"
  | "breakout"
  | "bursty"
  | "new_account";

export interface ChannelPerformerTile {
  video_url: string;
  /** From Cloud Run `_make_tile` — enables the R2 thumbnail fallback cascade. */
  video_id?: string;
  thumbnail_url: string;
  views: number;
  /** One of the 6 classify_format buckets (Cloud Run may send `format_label` instead). */
  content_format?: string;
  caption_snippet: string;
  /** ISO date string */
  posted_at: string;
  /** From Cloud Run `_make_tile` / corpus selectors */
  format_label?: string;
}

export interface ChannelUGCCreator {
  handle: string;
  /** Null when enrichment missed; never show as 0. */
  followers: number | null;
  avg_views: number;
  thumbnail_url: string;
  niche_slug: string;
  /** Representative video URL for the tile (may be empty) */
  sample_video_url?: string;
}

export interface ChannelRecommendation {
  index: number;
  title: string;
  body: string;
  kind?: "hero" | "regular" | "anti";
}

/** Deterministic metrics + educative captions (template-generated). */
export interface ChannelScoreCardData {
  trajectory_shape: TrajectoryShape;
  trajectory_delta_pct: number;
  percentile_in_niche: number;
  niche_p25: number;
  niche_p50: number;
  niche_p75: number;
  category_label: string;
  /** Two-axis — when ``content_class``, percentile row uses format cohort copy. */
  benchmark_axis?: "content_class" | "niche" | "none";
  peak_views: number;
  peak_date_iso: string | null;
  peak_age_months: number | null;
  recent_avg_views: number;
  posts_per_week: number;
  peer_median_posts_per_week: number;
  sample_size_videos: number;
}

export interface ChannelScoreCard extends ChannelScoreCardData {
  captions?: Record<string, string>;
}

export interface ChannelHashtagInsight {
  tag: string;
  count: number;
  avg_views: number;
  multiplier: number;
  caption?: string;
}

export interface ChannelNextVideoConcept {
  format: string;
  format_label: string;
  duration_sec: number;
  rationale_struct: string;
  sample_peer_handle: string;
  sample_video_url: string;
  sample_thumbnail_url?: string | null;
  peer_avg_views: number;
  channel_share_pct: number;
  /** Gemini narrative from `next_video` section when present */
  narrative?: string;
}

export interface ChannelPersona {
  dominant_format?: string;
  dominant_content_class_id?: number | null;
  content_class_label?: string;
}

/** One narrative section emitted by the server. */
export interface ChannelSection {
  section_id:
    | "verdict"
    | "what_worked"
    | "what_falling"
    | "video_vs_channel"
    | "competitive_landscape"
    | "hashtag_insights"
    | "next_video"
    | "recommendations"
    | "fallback"
    | (string & Record<never, never>);
  title: string;
  /** Accumulated text content for this section. */
  text: string;
  /** Video tiles embedded at section_start (what_worked / what_falling). */
  embedded_tiles?: ChannelPerformerTile[];
  /** Creator tiles (competitive_landscape only). */
  embedded_creators?: ChannelUGCCreator[];
  /** Hashtag table payload (hashtag_insights section). */
  hashtag_insights?: ChannelHashtagInsight[];
  /** Next-video concept (next_video section). */
  next_video?: ChannelNextVideoConcept;
}

/** F5 + F4 — corpus quick-peek and deep diagnosis finding row. */
export type ChannelDiagnosisFinding = {
  finding_id: string;
  teaser: string;
  strength: string;
  section_hint?: string;
};

/** Final payload from the `payload` event after streaming completes. */
export interface ChannelDiagnosisPayload {
  trajectory_shape: TrajectoryShape;
  sections: ChannelSection[];
  recommendations: ChannelRecommendation[];
  top_performers: ChannelPerformerTile[];
  worst_performers: ChannelPerformerTile[];
  ugc_creators: ChannelUGCCreator[];
  channel_pattern: {
    global_avg_views: number;
    total_videos: number;
    formats: Record<string, { count: number; avg_views: number; total_views: number }>;
  };
  inflection: Record<string, unknown> | null;
  creator_match: Record<string, unknown> | null;
  video_count: number;
  provenance: string;
  cache_hit: boolean;
  /** Legacy payloads only — prefer peer_source / score card. */
  niche_thin?: boolean;
  dominant_format?: string;
  score_card?: ChannelScoreCardData;
  score_card_captions?: Record<string, string>;
  verdict_tiles?: ChannelPerformerTile[];
  hashtag_insights?: ChannelHashtagInsight[];
  next_video?: ChannelNextVideoConcept | null;
  channel_persona?: ChannelPersona;
  /** corpus tier: content_class | niche_only | thin — null for pre-v2 cache rows */
  peer_source?: "content_class" | "niche_only" | "thin" | null;
  /** V5 §2 evidence rows for deep findings tile (post-2026-05 cache rows). */
  channel_findings?: ChannelDiagnosisFinding[];
}
