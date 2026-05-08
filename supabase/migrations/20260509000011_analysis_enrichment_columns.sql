ALTER TABLE public.video_corpus
  ADD COLUMN IF NOT EXISTS target_audience TEXT,
  ADD COLUMN IF NOT EXISTS pain_points     JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS promotion_type  TEXT DEFAULT 'organic',
  ADD COLUMN IF NOT EXISTS style_tags      JSONB DEFAULT '[]'::jsonb;

ALTER TABLE public.video_corpus
  DROP CONSTRAINT IF EXISTS video_corpus_promotion_type_check;

ALTER TABLE public.video_corpus
  ADD CONSTRAINT video_corpus_promotion_type_check
  CHECK (promotion_type IN ('organic', 'brand_deal', 'affiliate', 'self_promotion'));

CREATE INDEX IF NOT EXISTS idx_corpus_organic
  ON public.video_corpus (niche_id, indexed_at DESC)
  WHERE promotion_type = 'organic';
