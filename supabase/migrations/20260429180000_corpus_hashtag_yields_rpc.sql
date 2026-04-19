-- RPC for adaptive hashtag ordering / caps in corpus batch (14-day ingest yield).

CREATE OR REPLACE FUNCTION public.corpus_hashtag_yields_14d()
RETURNS TABLE (niche_id integer, hashtag text, ingest_count bigint)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  SELECT
    v.niche_id,
    lower(trim(both ' ' FROM trim(LEADING '#' FROM h))) AS hashtag,
    count(*)::bigint AS ingest_count
  FROM public.video_corpus v
  CROSS JOIN LATERAL unnest(coalesce(v.hashtags, ARRAY[]::text[])) AS u(h)
  WHERE v.created_at > (timezone('utc', now()) - interval '14 days')
    AND h IS NOT NULL
    AND trim(h) <> ''
  GROUP BY v.niche_id, lower(trim(both ' ' FROM trim(LEADING '#' FROM h)));
$$;

COMMENT ON FUNCTION public.corpus_hashtag_yields_14d() IS
  'Per-niche hashtag ingest counts (last 14d) for corpus pool hashtag ordering.';

GRANT EXECUTE ON FUNCTION public.corpus_hashtag_yields_14d() TO service_role;
