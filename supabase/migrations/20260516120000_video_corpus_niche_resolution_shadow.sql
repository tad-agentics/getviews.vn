-- HI-11 Phase 1 — Observability columns for two-axis niche resolution (shadow mode).
-- Populated on ingest; legacy niche_id + content_class_id remain resolver-driven until flip.

BEGIN;

ALTER TABLE public.video_corpus
  ADD COLUMN IF NOT EXISTS niche_resolution_source TEXT,
  ADD COLUMN IF NOT EXISTS niche_resolution_confidence DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS inferred_creator_niche_id INTEGER REFERENCES public.creator_niches(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.video_corpus.niche_resolution_source IS
  'Provenance: gemini_two_axis (HI-9 classification, conf≥0.6), hashtag (caption/hook substring resolver), default.';
COMMENT ON COLUMN public.video_corpus.niche_resolution_confidence IS
  'Gemini niche_classification.confidence when source=gemini_two_axis; NULL otherwise.';
COMMENT ON COLUMN public.video_corpus.inferred_creator_niche_id IS
  'Denormalized creator_niches.id from Gemini slug when source=gemini_two_axis; NULL when hashtag path.';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'video_corpus_niche_resolution_source_check'
  ) THEN
    ALTER TABLE public.video_corpus
      ADD CONSTRAINT video_corpus_niche_resolution_source_check
      CHECK (
        niche_resolution_source IS NULL
        OR niche_resolution_source IN ('gemini_two_axis', 'hashtag', 'default')
      );
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS video_corpus_niche_resolution_source_idx
  ON public.video_corpus (niche_resolution_source)
  WHERE niche_resolution_source IS NOT NULL;

COMMIT;
