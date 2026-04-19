-- B.3.1 — Channel formula cache for GET /channel/analyze (Phase B plan B.3).
-- Composite PK (handle, niche_id): one cached row per creator × ngách.
-- Writes: Cloud Run service_role upsert. Reads: authenticated SELECT (global cache).

CREATE TABLE IF NOT EXISTS public.channel_formulas (
  handle            TEXT    NOT NULL,
  niche_id          INTEGER NOT NULL REFERENCES public.niche_taxonomy (id) ON DELETE CASCADE,
  formula           JSONB   NOT NULL DEFAULT '[]'::jsonb,
  lessons           JSONB   NOT NULL DEFAULT '[]'::jsonb,
  top_hook          TEXT    NOT NULL DEFAULT '',
  optimal_length    TEXT    NOT NULL DEFAULT '',
  posting_time      TEXT    NOT NULL DEFAULT '',
  posting_cadence   TEXT    NOT NULL DEFAULT '',
  avg_views         BIGINT,
  engagement_pct    NUMERIC(10, 4),
  total_videos      INTEGER NOT NULL DEFAULT 0,
  bio               TEXT    NOT NULL DEFAULT '',
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (handle, niche_id)
);

CREATE INDEX IF NOT EXISTS idx_channel_formulas_niche_computed
  ON public.channel_formulas (niche_id, computed_at DESC);

ALTER TABLE public.channel_formulas ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users read channel_formulas" ON public.channel_formulas;

CREATE POLICY "Authenticated users read channel_formulas"
  ON public.channel_formulas FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

GRANT SELECT ON public.channel_formulas TO authenticated;

-- Aggregates for /channel/analyze (single index-friendly scan; RLS = caller).
CREATE OR REPLACE FUNCTION public.channel_corpus_stats(p_handle text, p_niche integer)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  SELECT jsonb_build_object(
    'total', (count(*))::bigint,
    'avg_views', coalesce((avg(v.views))::bigint, 0),
    'avg_er', coalesce(avg(v.engagement_rate), 0)::float
  )
  FROM public.video_corpus v
  WHERE v.niche_id = p_niche
    AND lower(v.creator_handle) = lower(trim(both from p_handle));
$$;

REVOKE ALL ON FUNCTION public.channel_corpus_stats(text, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.channel_corpus_stats(text, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.channel_corpus_stats(text, integer) TO service_role;
