-- Channel diagnosis v2 — structured score card, verdict tiles, hashtag block, next-video, persona, peer source.

ALTER TABLE public.channel_diagnoses
  ADD COLUMN IF NOT EXISTS score_card jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS verdict_tiles jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS hashtag_insights jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS next_video jsonb,
  ADD COLUMN IF NOT EXISTS channel_persona jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS peer_source text;

COMMENT ON COLUMN public.channel_diagnoses.score_card IS
  'TLDR: trajectory delta, percentile buckets, peak/recent, cadence, best hour (+ captions client-side or stored).';
COMMENT ON COLUMN public.channel_diagnoses.verdict_tiles IS
  'Peak + recent video tiles for verdict section evidence.';
COMMENT ON COLUMN public.channel_diagnoses.hashtag_insights IS
  'Top hashtags: tag, count, avg_views, multiplier vs channel avg.';
COMMENT ON COLUMN public.channel_diagnoses.next_video IS
  'Next-video concept: format, peer sample, hook/premise/rationale from model.';
COMMENT ON COLUMN public.channel_diagnoses.channel_persona IS
  'Dominant_format + content_class_id + Vietnamese label.';
COMMENT ON COLUMN public.channel_diagnoses.peer_source IS
  'content_class | niche_only | thin — NULL for rows written before v2.';

-- Allow authenticated clients to call map helper for persona fallback (RLS still applies on reads).
GRANT EXECUTE ON FUNCTION public.map_legacy_corpus_to_content_class(integer, text) TO authenticated, anon;
