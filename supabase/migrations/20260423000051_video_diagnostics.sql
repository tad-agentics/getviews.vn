-- Phase B · B.1.1 — video_diagnostics cache for /video deterministic screen.
--
-- Cloud Run (service_role) upserts after video_structural + LLM slots fill.
-- Clients read via Supabase or via Cloud Run proxy — same row shape as
-- `VideoAnalyzeResponse` in `src/lib/api-types.ts`.
--
-- JSONB shapes (see phase-b-plan.md):
--   lessons, hook_phases, segments — win + shared structure
--   flop_issues — flop mode only
--   retention_curve, niche_benchmark_curve — optional until B.1.2

CREATE TABLE video_diagnostics (
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

CREATE INDEX idx_video_diagnostics_computed_at
  ON video_diagnostics (computed_at DESC);

ALTER TABLE video_diagnostics ENABLE ROW LEVEL SECURITY;

-- Match corpus read model: any signed-in user may read diagnostics.
CREATE POLICY "Authenticated users can read video_diagnostics"
  ON video_diagnostics FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

-- No INSERT/UPDATE/DELETE for authenticated — pipeline uses service_role.

GRANT SELECT ON video_diagnostics TO authenticated;
