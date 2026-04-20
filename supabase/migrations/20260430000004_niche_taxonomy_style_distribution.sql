-- Phase C.3.1 — style distribution for Ideas format (stored on taxonomy; niche_intelligence is a materialized view).

ALTER TABLE public.niche_taxonomy
  ADD COLUMN IF NOT EXISTS style_distribution JSONB NOT NULL DEFAULT '[]';

COMMENT ON COLUMN public.niche_taxonomy.style_distribution IS 'Phase C Ideas — aggregated style buckets for report_ideas.py';
