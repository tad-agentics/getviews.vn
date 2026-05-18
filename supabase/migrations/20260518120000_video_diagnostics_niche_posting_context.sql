-- Cached heatmap + variance payload for embedding niche posting timing in
-- video diagnosis UI (SSE narrative_ready + video_diagnostics cache parity).

ALTER TABLE public.video_diagnostics
  ADD COLUMN IF NOT EXISTS niche_posting_context JSONB;

COMMENT ON COLUMN public.video_diagnostics.niche_posting_context IS
  'Deterministic 7×8 grid + variance + top windows for diagnosis heatmap UI; '
  'null when niche sample below threshold or compute failed.';
