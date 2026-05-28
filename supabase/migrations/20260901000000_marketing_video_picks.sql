-- Marketing Corpus Pick API — pick history + selection RPCs (service_role only).
--
-- Edge Function proxies to Cloud Run batch, which:
--   1. select_marketing_corpus_video() — weighted random eligible row
--   2. run_video_analyze_pipeline (basic/win)
--   3. record_marketing_video_pick() on success

BEGIN;

CREATE TABLE IF NOT EXISTS public.marketing_video_picks (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id           TEXT NOT NULL UNIQUE REFERENCES public.video_corpus (video_id) ON DELETE CASCADE,
  creator_niche_id   INTEGER NOT NULL REFERENCES public.creator_niches (id),
  priority_weight    SMALLINT NOT NULL CHECK (priority_weight BETWEEN 1 AND 3),
  analysis_depth     TEXT NOT NULL DEFAULT 'basic' CHECK (analysis_depth IN ('basic', 'deep')),
  picked_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marketing_video_picks_niche_picked
  ON public.marketing_video_picks (creator_niche_id, picked_at DESC);

CREATE INDEX IF NOT EXISTS idx_marketing_video_picks_picked_at
  ON public.marketing_video_picks (picked_at DESC);

ALTER TABLE public.marketing_video_picks ENABLE ROW LEVEL SECURITY;

-- No policies — only service_role (bypasses RLS) and SECURITY DEFINER RPCs.

COMMENT ON TABLE public.marketing_video_picks IS
  'Videos returned by the marketing corpus pick API. Excludes re-picks.';

-- ── Weighted niche config (creator_niche_id, priority_weight) ─────────────
-- 3 = highest, 1 = lowest per product brief.

CREATE OR REPLACE FUNCTION public.select_marketing_corpus_video()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row RECORD;
  v_niche_id INT;
  v_weight SMALLINT;
BEGIN
  WITH niche_weights AS (
    SELECT *
    FROM (
      VALUES
        (1::INT, 3::SMALLINT),
        (2, 3),
        (3, 3),
        (5, 3),
        (6, 2),
        (9, 1),
        (10, 1),
        (12, 1),
        (14, 2),
        (16, 1)
    ) AS t(creator_niche_id, priority_weight)
  ),
  eligible AS (
    SELECT
      vc.video_id,
      vc.tiktok_url,
      vc.creator_handle,
      vc.views,
      vc.caption,
      vc.hook_phrase,
      vc.hook_type,
      vc.thumbnail_url,
      vc.posted_at,
      vc.breakout_multiplier,
      vc.content_type,
      vc.inferred_creator_niche_id,
      nw.priority_weight
    FROM public.video_corpus vc
    INNER JOIN niche_weights nw
      ON nw.creator_niche_id = vc.inferred_creator_niche_id
    WHERE vc.views > 100000
      AND vc.content_class_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1
        FROM public.marketing_video_picks mp
        WHERE mp.video_id = vc.video_id
      )
  ),
  weighted_niches AS (
    SELECT nw.creator_niche_id, nw.priority_weight
    FROM niche_weights nw
    WHERE EXISTS (
      SELECT 1
      FROM eligible e
      WHERE e.inferred_creator_niche_id = nw.creator_niche_id
    )
  ),
  niche_roulette AS (
    SELECT wn.creator_niche_id, wn.priority_weight
    FROM weighted_niches wn,
    LATERAL generate_series(1, wn.priority_weight)
  ),
  picked_niche AS (
    SELECT nr.creator_niche_id, nr.priority_weight
    FROM niche_roulette nr
    ORDER BY random()
    LIMIT 1
  ),
  picked_video AS (
    SELECT
      e.video_id,
      e.tiktok_url,
      e.creator_handle,
      e.views,
      e.caption,
      e.hook_phrase,
      e.hook_type,
      e.thumbnail_url,
      e.posted_at,
      e.breakout_multiplier,
      e.content_type,
      e.inferred_creator_niche_id,
      e.priority_weight
    FROM eligible e
    INNER JOIN picked_niche pn
      ON pn.creator_niche_id = e.inferred_creator_niche_id
    ORDER BY random()
    LIMIT 1
  )
  SELECT
    pv.video_id,
    pv.tiktok_url,
    pv.creator_handle,
    pv.views,
    pv.caption,
    pv.hook_phrase,
    pv.hook_type,
    pv.thumbnail_url,
    pv.posted_at,
    pv.breakout_multiplier,
    pv.content_type,
    pv.inferred_creator_niche_id,
    pv.priority_weight,
    cn.slug AS creator_niche_slug,
    cn.name_vn AS creator_niche_name_vn
  INTO v_row
  FROM picked_video pv
  LEFT JOIN public.creator_niches cn
    ON cn.id = pv.inferred_creator_niche_id;

  IF v_row.video_id IS NULL THEN
    RAISE EXCEPTION 'marketing_pool_exhausted'
      USING ERRCODE = 'P0001';
  END IF;

  RETURN jsonb_build_object(
    'video_id', v_row.video_id,
    'tiktok_url', v_row.tiktok_url,
    'creator_handle', v_row.creator_handle,
    'views', v_row.views,
    'caption', v_row.caption,
    'hook_phrase', v_row.hook_phrase,
    'hook_type', v_row.hook_type,
    'thumbnail_url', v_row.thumbnail_url,
    'posted_at', v_row.posted_at,
    'breakout_multiplier', v_row.breakout_multiplier,
    'content_type', v_row.content_type,
    'creator_niche_id', v_row.inferred_creator_niche_id,
    'priority_weight', v_row.priority_weight,
    'creator_niche_slug', v_row.creator_niche_slug,
    'creator_niche_name_vn', v_row.creator_niche_name_vn
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.record_marketing_video_pick(
  p_video_id TEXT,
  p_creator_niche_id INT,
  p_priority_weight SMALLINT,
  p_analysis_depth TEXT DEFAULT 'basic'
)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_picked_at TIMESTAMPTZ;
BEGIN
  IF p_analysis_depth NOT IN ('basic', 'deep') THEN
    RAISE EXCEPTION 'invalid_analysis_depth';
  END IF;

  INSERT INTO public.marketing_video_picks (
    video_id,
    creator_niche_id,
    priority_weight,
    analysis_depth
  )
  VALUES (
    p_video_id,
    p_creator_niche_id,
    p_priority_weight,
    p_analysis_depth
  )
  ON CONFLICT (video_id) DO NOTHING
  RETURNING picked_at INTO v_picked_at;

  IF v_picked_at IS NULL THEN
    SELECT picked_at INTO v_picked_at
    FROM public.marketing_video_picks
    WHERE video_id = p_video_id;
  END IF;

  RETURN v_picked_at;
END;
$$;

REVOKE ALL ON FUNCTION public.select_marketing_corpus_video() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.select_marketing_corpus_video() FROM anon;
REVOKE ALL ON FUNCTION public.select_marketing_corpus_video() FROM authenticated;
GRANT EXECUTE ON FUNCTION public.select_marketing_corpus_video() TO service_role;

REVOKE ALL ON FUNCTION public.record_marketing_video_pick(TEXT, INT, SMALLINT, TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.record_marketing_video_pick(TEXT, INT, SMALLINT, TEXT) FROM anon;
REVOKE ALL ON FUNCTION public.record_marketing_video_pick(TEXT, INT, SMALLINT, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.record_marketing_video_pick(TEXT, INT, SMALLINT, TEXT) TO service_role;

COMMENT ON FUNCTION public.select_marketing_corpus_video() IS
  'Marketing API — weighted random corpus video (>100k views, 10 niches, not yet picked).';

COMMENT ON FUNCTION public.record_marketing_video_pick(TEXT, INT, SMALLINT, TEXT) IS
  'Marketing API — record a successful pick after analysis completes. Service-role only.';

COMMIT;
