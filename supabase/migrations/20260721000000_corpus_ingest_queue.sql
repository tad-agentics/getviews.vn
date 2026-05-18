-- Queue for high-views TikTok references discovered during live diagnosis (EnsembleData).
-- Batch pod drains via POST /batch/process-ingest-queue → run_reingest_video_items.

CREATE TABLE IF NOT EXISTS public.corpus_ingest_queue (
  id             BIGSERIAL PRIMARY KEY,
  aweme_id       TEXT NOT NULL UNIQUE,
  aweme_url      TEXT,
  niche_id       INTEGER REFERENCES public.niche_taxonomy (id),
  niche_label    TEXT,
  views          BIGINT,
  desc_snippet   TEXT,
  thumbnail_url  TEXT,
  thumbnail_r2_url TEXT,
  ingest_reason  TEXT NOT NULL DEFAULT 'reference_live_search',
  queued_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_corpus_ingest_queue_pending
  ON public.corpus_ingest_queue (queued_at)
  WHERE processed_at IS NULL;

ALTER TABLE public.corpus_ingest_queue ENABLE ROW LEVEL SECURITY;

-- Extend video_corpus.ingest_source for reference queue provenance.
ALTER TABLE public.video_corpus DROP CONSTRAINT IF EXISTS video_corpus_ingest_source_check;
ALTER TABLE public.video_corpus ADD CONSTRAINT video_corpus_ingest_source_check CHECK (
  ingest_source IS NULL OR ingest_source IN (
    'batch_nightly',
    'user_diagnosis',
    'douyin_batch',
    'reference_live_search'
  )
);
