-- Wave 3 W3-1 — partition video_diagnostics cache by analysis_depth (§4.12.3).
-- Cohort canonical remains content_class; this key is product depth (basic | deep).

BEGIN;

ALTER TABLE public.video_diagnostics
  ADD COLUMN IF NOT EXISTS analysis_depth TEXT NOT NULL DEFAULT 'deep'
    CHECK (analysis_depth IN ('basic', 'deep'));

COMMENT ON COLUMN public.video_diagnostics.analysis_depth IS
  'Product depth for on-demand / corpus diagnosis cache — basic (whitelist) vs deep (full pool).';

-- Existing rows ≈ full-pool behavior → deep.
UPDATE public.video_diagnostics
SET analysis_depth = 'deep'
WHERE analysis_depth IS DISTINCT FROM 'deep';

ALTER TABLE public.video_diagnostics
  DROP CONSTRAINT IF EXISTS video_diagnostics_pkey;

ALTER TABLE public.video_diagnostics
  ADD PRIMARY KEY (video_id, analysis_depth);

CREATE INDEX IF NOT EXISTS idx_video_diagnostics_tiktok_url_depth
  ON public.video_diagnostics (tiktok_url, analysis_depth)
  WHERE tiktok_url IS NOT NULL;

COMMIT;
