-- Phase B · B.1.1 — video_diagnostics cache for /video deterministic screen.
--
-- Idempotent: production may already have this object from Supabase MCP
-- migration `video_diagnostics_phase_b`. Fresh `supabase db push` / clones
-- still converge to the same schema.
--
-- Cloud Run (service_role) upserts after video_structural + LLM slots fill.
-- JSONB shapes: see `artifacts/plans/phase-b-plan.md`.

CREATE TABLE IF NOT EXISTS video_diagnostics (
  video_id                TEXT PRIMARY KEY REFERENCES video_corpus (video_id) ON DELETE CASCADE,
  analysis_headline       TEXT,
  analysis_subtext        TEXT,
  lessons                 JSONB NOT NULL DEFAULT '[]',
  hook_phases             JSONB NOT NULL DEFAULT '[]',
  segments                JSONB NOT NULL DEFAULT '[]',
  flop_issues             JSONB,
  retention_curve         JSONB,
  niche_benchmark_curve   JSONB,
  computed_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_video_diagnostics_computed_at
  ON video_diagnostics (computed_at DESC);

ALTER TABLE video_diagnostics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read video_diagnostics" ON video_diagnostics;

CREATE POLICY "Authenticated users can read video_diagnostics"
  ON video_diagnostics FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

GRANT SELECT ON video_diagnostics TO authenticated;
