-- Cache the narrative layer of the video diagnosis report so the
-- Gemini synthesis call (synthesize_diagnosis_v2) doesn't re-fire on
-- every 1h cache hit.
--
-- Before this change, routers/video.py invoked
-- finalize_video_narrative_layer unconditionally after every
-- run_video_analyze_pipeline call. The deterministic layer
-- (flop_issues, hook_phases, segments, retention_curve,
-- niche_benchmark_curve) was cached in video_diagnostics, but the
-- narrative layer (narrative_vi, format_cards, diagnosis,
-- performance_tier, bright_spot_signal, view_scenarios,
-- channel_context, reference_videos) was recomputed every request —
-- a hundreds-of-tokens Gemini completion per cache hit. Real cost
-- bleed at scale.
--
-- Add the missing columns, write them in the same upsert that fills
-- the deterministic layer, and let finalize_video_narrative_layer
-- early-return on cache hit when narrative_vi is already present.

ALTER TABLE video_diagnostics
  ADD COLUMN IF NOT EXISTS narrative_vi       JSONB,
  ADD COLUMN IF NOT EXISTS format_cards       JSONB,
  ADD COLUMN IF NOT EXISTS diagnosis          TEXT,
  ADD COLUMN IF NOT EXISTS performance_tier   TEXT,
  ADD COLUMN IF NOT EXISTS bright_spot_signal JSONB,
  ADD COLUMN IF NOT EXISTS view_scenarios     JSONB,
  ADD COLUMN IF NOT EXISTS channel_context    JSONB,
  ADD COLUMN IF NOT EXISTS reference_videos   JSONB;

COMMENT ON COLUMN video_diagnostics.narrative_vi IS
  'Cached Gemini narrative synthesis output (NarrativeVi shape). Null when '
  'pre-narrative-cache rows or when the Call-2 synthesis failed; '
  'finalize_video_narrative_layer recomputes on miss.';

COMMENT ON COLUMN video_diagnostics.performance_tier IS
  'Cached refined tier: hit | average | flop | unknown. Combined corpus + '
  'channel-context verdict produced by refine_performance_tier.';
