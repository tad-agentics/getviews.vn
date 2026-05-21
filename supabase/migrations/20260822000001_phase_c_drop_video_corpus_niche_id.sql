-- Phase C (2026-05-21): drop legacy ``video_corpus.niche_id``.
-- Class-first canonical cohort = ``content_class_id``; ingest loop bucket = ``ingest_loop_niche_id``.

BEGIN;

-- Backfill loop bucket from legacy column before drop (idempotent).
UPDATE public.video_corpus
SET ingest_loop_niche_id = niche_id
WHERE ingest_loop_niche_id IS NULL
  AND niche_id IS NOT NULL;

-- ── Nullable bridge (no-op if already nullable) ─────────────────────────────
ALTER TABLE public.video_corpus
  ALTER COLUMN niche_id DROP NOT NULL;

-- ── Defensive trigger: map from ingest loop bucket, not dropped column ────────
CREATE OR REPLACE FUNCTION video_corpus_fill_content_class_id()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.content_class_id IS NULL AND NEW.ingest_loop_niche_id IS NOT NULL THEN
    NEW.content_class_id := map_legacy_corpus_to_content_class(
      NEW.ingest_loop_niche_id, NEW.content_format
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_video_corpus_fill_content_class_id ON public.video_corpus;

CREATE TRIGGER trg_video_corpus_fill_content_class_id
  BEFORE INSERT OR UPDATE OF ingest_loop_niche_id, content_format ON public.video_corpus
  FOR EACH ROW
  EXECUTE FUNCTION video_corpus_fill_content_class_id();

-- ── RPCs / functions that referenced video_corpus.niche_id ─────────────────

CREATE OR REPLACE FUNCTION public.daily_corpus_growth_by_niche(p_since TIMESTAMPTZ)
RETURNS TABLE (niche_id INT, niche_name TEXT, delta_24h BIGINT)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    vc.ingest_loop_niche_id,
    COALESCE(nt.name_en, nt.name_vn, vc.ingest_loop_niche_id::text) AS niche_name,
    COUNT(*) AS delta_24h
  FROM public.video_corpus vc
  LEFT JOIN public.niche_taxonomy nt ON nt.id = vc.ingest_loop_niche_id
  WHERE vc.indexed_at >= p_since
    AND vc.ingest_loop_niche_id IS NOT NULL
  GROUP BY vc.ingest_loop_niche_id, nt.name_en, nt.name_vn
  ORDER BY COUNT(*) DESC;
$$;

CREATE OR REPLACE FUNCTION public.corpus_hashtag_yields_14d()
RETURNS TABLE (niche_id integer, hashtag text, ingest_count bigint)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  SELECT
    v.ingest_loop_niche_id,
    lower(trim(both ' ' FROM trim(LEADING '#' FROM h))) AS hashtag,
    count(*)::bigint AS ingest_count
  FROM public.video_corpus v
  CROSS JOIN LATERAL unnest(coalesce(v.hashtags, ARRAY[]::text[])) AS u(h)
  WHERE v.created_at > (timezone('utc', now()) - interval '14 days')
    AND v.ingest_loop_niche_id IS NOT NULL
    AND h IS NOT NULL
    AND trim(h) <> ''
  GROUP BY v.ingest_loop_niche_id, lower(trim(both ' ' FROM trim(LEADING '#' FROM h)));
$$;

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
  WHERE v.ingest_loop_niche_id = p_niche
    AND lower(v.creator_handle) = lower(trim(both from p_handle));
$$;

CREATE OR REPLACE FUNCTION public.cross_creator_pattern_aggregate(p_lookback_days integer DEFAULT 7)
RETURNS TABLE (
  niche_id integer,
  hook_type text,
  creator_count bigint,
  total_views bigint,
  creators text[]
)
LANGUAGE sql
STABLE
SET search_path = public
AS $$
  SELECT
    v.ingest_loop_niche_id,
    v.hook_type,
    (COUNT(DISTINCT v.creator_handle))::bigint AS creator_count,
    COALESCE(SUM(v.views), 0)::bigint AS total_views,
    COALESCE(
      array_agg(DISTINCT v.creator_handle) FILTER (WHERE v.creator_handle IS NOT NULL),
      ARRAY[]::text[]
    ) AS creators
  FROM video_corpus v
  WHERE v.indexed_at > NOW() - make_interval(days => p_lookback_days)
    AND v.ingest_loop_niche_id IS NOT NULL
    AND v.hook_type IS NOT NULL
    AND v.creator_handle IS NOT NULL
  GROUP BY v.ingest_loop_niche_id, v.hook_type
  HAVING COUNT(DISTINCT v.creator_handle) >= 3
  ORDER BY COALESCE(SUM(v.views), 0) DESC;
$$;

CREATE OR REPLACE FUNCTION public.pattern_wow_diff_7d(p_niche_id INT)
RETURNS TABLE (
  hook_type   TEXT,
  rank_now    INT,
  rank_prior  INT,
  rank_change INT,
  is_new      BOOLEAN,
  is_dropped  BOOLEAN
)
LANGUAGE sql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
  WITH
    now_window AS (
      SELECT v.hook_type, count(*) AS n_videos, COALESCE(sum(v.views), 0) AS sum_views
      FROM public.video_corpus v
      WHERE v.ingest_loop_niche_id = p_niche_id
        AND v.hook_type IS NOT NULL AND btrim(v.hook_type) <> ''
        AND v.created_at >= now() - INTERVAL '7 days'
      GROUP BY v.hook_type
    ),
    now_ranked AS (
      SELECT hook_type, rank() OVER (ORDER BY n_videos DESC, sum_views DESC) AS r FROM now_window
    ),
    now_top AS (SELECT hook_type, r::INT AS rank_now FROM now_ranked WHERE r <= 10),
    prior_window AS (
      SELECT v.hook_type, count(*) AS n_videos, COALESCE(sum(v.views), 0) AS sum_views
      FROM public.video_corpus v
      WHERE v.ingest_loop_niche_id = p_niche_id
        AND v.hook_type IS NOT NULL AND btrim(v.hook_type) <> ''
        AND v.created_at >= now() - INTERVAL '14 days'
        AND v.created_at <  now() - INTERVAL '7 days'
      GROUP BY v.hook_type
    ),
    prior_ranked AS (
      SELECT hook_type, rank() OVER (ORDER BY n_videos DESC, sum_views DESC) AS r FROM prior_window
    ),
    prior_top AS (SELECT hook_type, r::INT AS rank_prior FROM prior_ranked WHERE r <= 10)
  SELECT
    COALESCE(n.hook_type, p.hook_type) AS hook_type,
    n.rank_now,
    p.rank_prior,
    CASE
      WHEN n.rank_now IS NULL OR p.rank_prior IS NULL THEN NULL
      ELSE (p.rank_prior - n.rank_now)
    END AS rank_change,
    (n.rank_now IS NOT NULL AND p.rank_prior IS NULL) AS is_new,
    (n.rank_now IS NULL AND p.rank_prior IS NOT NULL) AS is_dropped
  FROM now_top n
  FULL OUTER JOIN prior_top p ON p.hook_type = n.hook_type
  ORDER BY COALESCE(n.rank_now, 99), COALESCE(p.rank_prior, 99);
$$;

CREATE OR REPLACE FUNCTION public.seed_starter_creators(p_top_n INTEGER DEFAULT 10)
RETURNS TABLE (out_niche_id INTEGER, out_seeded INTEGER)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  WITH ranked AS (
    SELECT
      v.ingest_loop_niche_id AS r_niche_id,
      v.creator_handle AS handle,
      MAX(COALESCE(v.creator_followers, 0)) AS followers,
      AVG(COALESCE(v.views, 0))::BIGINT AS avg_views,
      COUNT(*)::INT AS video_count,
      ROW_NUMBER() OVER (
        PARTITION BY v.ingest_loop_niche_id
        ORDER BY MAX(COALESCE(v.creator_followers, 0)) DESC, COUNT(*) DESC
      ) AS rk
    FROM video_corpus v
    WHERE v.creator_handle IS NOT NULL
      AND v.creator_handle <> ''
      AND v.ingest_loop_niche_id IS NOT NULL
    GROUP BY v.ingest_loop_niche_id, v.creator_handle
  ),
  touched AS (
    INSERT INTO starter_creators (
      niche_id, handle, display_name, followers, avg_views,
      video_count, is_curated, rank, last_seeded_at
    )
    SELECT r.r_niche_id, r.handle, NULL, r.followers, r.avg_views,
           r.video_count, FALSE, r.rk::INT, now()
    FROM ranked r
    WHERE r.rk <= p_top_n
    ON CONFLICT (niche_id, handle) DO UPDATE
      SET followers = EXCLUDED.followers,
          avg_views = EXCLUDED.avg_views,
          video_count = EXCLUDED.video_count,
          rank = EXCLUDED.rank,
          last_seeded_at = now()
      WHERE starter_creators.is_curated = FALSE
    RETURNING starter_creators.niche_id AS t_niche_id
  )
  SELECT t.t_niche_id, COUNT(*)::INT FROM touched t GROUP BY t.t_niche_id;
END;
$$;

-- timing_top_window_streak (3-arg): corpus filter on ingest_loop_niche_id
CREATE OR REPLACE FUNCTION public.timing_top_window_streak(
  p_niche_id INT,
  p_day INT,
  p_hour_bucket INT
) RETURNS INTEGER
LANGUAGE plpgsql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  streak INT := 0;
  rec RECORD;
BEGIN
  IF p_day IS NULL OR p_hour_bucket IS NULL OR p_niche_id IS NULL THEN
    RETURN 0;
  END IF;

  FOR rec IN
    WITH weeks AS (
      SELECT generate_series(0, 7) AS week_idx
    ),
    corpus_evt AS (
      SELECT
        w.week_idx,
        COALESCE(v.posted_at, v.indexed_at, v.created_at) AS evt,
        v.views
      FROM weeks w
      INNER JOIN public.video_corpus v
        ON v.ingest_loop_niche_id = p_niche_id
       AND COALESCE(v.posted_at, v.indexed_at, v.created_at) >= now() - ((w.week_idx + 1) * INTERVAL '7 days')
       AND COALESCE(v.posted_at, v.indexed_at, v.created_at) <  now() - (w.week_idx * INTERVAL '7 days')
    ),
    per_week AS (
      SELECT
        week_idx,
        ((EXTRACT(ISODOW FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh'))::INT - 1) % 7) AS dow,
        CASE
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 6 THEN 7
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 9 THEN 0
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 12 THEN 1
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 15 THEN 2
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 18 THEN 3
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 20 THEN 4
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 22 THEN 5
          ELSE 6
        END AS hour_bucket,
        COUNT(*) AS n,
        COALESCE(SUM(views), 0) AS sv
      FROM corpus_evt
      GROUP BY week_idx,
        ((EXTRACT(ISODOW FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh'))::INT - 1) % 7),
        CASE
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 6 THEN 7
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 9 THEN 0
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 12 THEN 1
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 15 THEN 2
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 18 THEN 3
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 20 THEN 4
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 22 THEN 5
          ELSE 6
        END
    ),
    ranked AS (
      SELECT
        week_idx, dow, hour_bucket,
        ROW_NUMBER() OVER (
          PARTITION BY week_idx ORDER BY n DESC, sv DESC, dow ASC, hour_bucket ASC
        ) AS rn
      FROM per_week
    )
    SELECT week_idx, dow, hour_bucket
    FROM ranked
    WHERE rn = 1
    ORDER BY week_idx ASC
  LOOP
    IF rec.dow = p_day AND rec.hour_bucket = p_hour_bucket THEN
      streak := streak + 1;
    ELSE
      EXIT;
    END IF;
  END LOOP;

  RETURN streak;
END;
$$;

-- ── upsert_video_corpus_batch (no niche_id) ─────────────────────────────────
DROP FUNCTION IF EXISTS upsert_video_corpus_batch(jsonb);

CREATE OR REPLACE FUNCTION upsert_video_corpus_batch(p_rows JSONB)
RETURNS TABLE (out_video_id TEXT, out_action TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
#variable_conflict use_variable
DECLARE
    r JSONB;
    v_video_id TEXT;
    v_existing_cc INTEGER;
    v_new_cc INTEGER;
BEGIN
    FOR r IN SELECT * FROM jsonb_array_elements(p_rows)
    LOOP
        v_video_id := r->>'video_id';
        v_new_cc := NULLIF(r->>'content_class_id', '')::INTEGER;

        SELECT content_class_id INTO v_existing_cc
        FROM video_corpus
        WHERE video_id = v_video_id;

        INSERT INTO video_corpus (
            video_id, content_type, content_class_id, creator_handle, tiktok_url,
            thumbnail_url, video_url, frame_urls, analysis_json,
            views, likes, comments, shares, engagement_rate,
            indexed_at,
            ingest_source, first_seen_at, last_refreshed_at, quality_tier,
            niche_resolution_source, niche_resolution_confidence, inferred_creator_niche_id,
            ingest_loop_niche_id, ingest_loop_content_class_id,
            class_assignment_tier, class_assignment_disagreement, score_cohort_mismatch
        )
        VALUES (
            v_video_id,
            COALESCE(r->>'content_type', 'video'),
            v_new_cc,
            COALESCE(r->>'creator_handle', ''),
            COALESCE(r->>'tiktok_url', ''),
            r->>'thumbnail_url',
            r->>'video_url',
            COALESCE((r->'frame_urls')::TEXT::TEXT[], '{}'),
            COALESCE(r->'analysis_json', '{}'),
            COALESCE((r->>'views')::BIGINT, 0),
            COALESCE((r->>'likes')::BIGINT, 0),
            COALESCE((r->>'comments')::BIGINT, 0),
            COALESCE((r->>'shares')::BIGINT, 0),
            COALESCE((r->>'engagement_rate')::NUMERIC, 0),
            COALESCE((r->>'indexed_at')::TIMESTAMPTZ, now()),
            COALESCE(r->>'ingest_source', 'batch_nightly'),
            COALESCE((r->>'first_seen_at')::TIMESTAMPTZ, now()),
            now(),
            COALESCE(r->>'quality_tier', 'high'),
            r->>'niche_resolution_source',
            NULLIF(r->>'niche_resolution_confidence', '')::DOUBLE PRECISION,
            NULLIF(r->>'inferred_creator_niche_id', '')::INTEGER,
            NULLIF(r->>'ingest_loop_niche_id', '')::INTEGER,
            NULLIF(r->>'ingest_loop_content_class_id', '')::INTEGER,
            r->>'class_assignment_tier',
            NULLIF(r->>'class_assignment_disagreement', '')::DOUBLE PRECISION,
            COALESCE((r->>'score_cohort_mismatch')::BOOLEAN, FALSE)
        )
        ON CONFLICT (video_id) DO UPDATE SET
            content_type        = EXCLUDED.content_type,
            content_class_id    = EXCLUDED.content_class_id,
            creator_handle      = EXCLUDED.creator_handle,
            tiktok_url          = EXCLUDED.tiktok_url,
            thumbnail_url       = COALESCE(EXCLUDED.thumbnail_url, video_corpus.thumbnail_url),
            video_url           = COALESCE(EXCLUDED.video_url, video_corpus.video_url),
            frame_urls          = EXCLUDED.frame_urls,
            analysis_json       = EXCLUDED.analysis_json,
            views               = EXCLUDED.views,
            likes               = EXCLUDED.likes,
            comments            = EXCLUDED.comments,
            shares              = EXCLUDED.shares,
            engagement_rate     = EXCLUDED.engagement_rate,
            indexed_at          = EXCLUDED.indexed_at,
            ingest_source       = COALESCE(video_corpus.ingest_source, EXCLUDED.ingest_source),
            first_seen_at       = COALESCE(video_corpus.first_seen_at, EXCLUDED.first_seen_at),
            last_refreshed_at   = now(),
            quality_tier        = COALESCE(video_corpus.quality_tier, EXCLUDED.quality_tier),
            niche_resolution_source      = EXCLUDED.niche_resolution_source,
            niche_resolution_confidence  = EXCLUDED.niche_resolution_confidence,
            inferred_creator_niche_id    = EXCLUDED.inferred_creator_niche_id,
            ingest_loop_niche_id         = COALESCE(EXCLUDED.ingest_loop_niche_id, video_corpus.ingest_loop_niche_id),
            ingest_loop_content_class_id = COALESCE(EXCLUDED.ingest_loop_content_class_id, video_corpus.ingest_loop_content_class_id),
            class_assignment_tier        = COALESCE(EXCLUDED.class_assignment_tier, video_corpus.class_assignment_tier),
            class_assignment_disagreement = COALESCE(EXCLUDED.class_assignment_disagreement, video_corpus.class_assignment_disagreement),
            score_cohort_mismatch        = EXCLUDED.score_cohort_mismatch;

        RETURN QUERY SELECT v_video_id, 'upserted'::TEXT;
    END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION upsert_video_corpus_batch(JSONB) TO service_role;

COMMENT ON FUNCTION upsert_video_corpus_batch(JSONB) IS
  'Phase C — class-first batch upsert; no video_corpus.niche_id.';

-- ── Recreate class MVs without SELECT * (drops niche_id column dependency) ─
DROP MATERIALIZED VIEW IF EXISTS content_class_tier_intelligence CASCADE;
DROP MATERIALIZED VIEW IF EXISTS content_class_intelligence CASCADE;

CREATE MATERIALIZED VIEW content_class_intelligence AS
WITH base AS (
  SELECT
    content_class_id, hook_type, tone, views, engagement_rate, face_appears_at,
    transitions_per_second, video_duration, text_overlay_count, is_commerce,
    dialect, cta_type, has_vietnamese_hashtags, has_caption_text, hashtag_count,
    is_original_sound, scene_count
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
),
hook_dist AS (
  SELECT content_class_id, jsonb_object_agg(hook_type, cnt) AS hook_distribution
  FROM (
    SELECT content_class_id, hook_type, COUNT(*) AS cnt
    FROM base WHERE hook_type IS NOT NULL
    GROUP BY content_class_id, hook_type
  ) x
  GROUP BY content_class_id
),
tone_dist AS (
  SELECT content_class_id, jsonb_object_agg(tone, cnt) AS tone_distribution
  FROM (
    SELECT content_class_id, tone, COUNT(*) AS cnt
    FROM base WHERE tone IS NOT NULL
    GROUP BY content_class_id, tone
  ) x
  GROUP BY content_class_id
),
agg AS (
  SELECT
    b.content_class_id,
    COUNT(*) AS sample_size,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS median_views,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS p50_views,
    AVG(b.views) AS avg_views,
    AVG(b.engagement_rate) AS avg_engagement_rate,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) AS median_er,
    AVG(b.face_appears_at) FILTER (WHERE b.face_appears_at IS NOT NULL) AS avg_face_appears_at,
    COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL AND b.face_appears_at <= 0.5) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.face_appears_at IS NOT NULL), 0) AS pct_face_in_half_sec,
    AVG(b.transitions_per_second) AS avg_transitions_per_second,
    AVG(b.video_duration) AS avg_duration,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.video_duration) AS median_duration,
    MIN(b.video_duration) AS min_duration,
    MAX(b.video_duration) AS max_duration,
    AVG(b.text_overlay_count) AS avg_text_overlays,
    COUNT(*) FILTER (WHERE b.is_commerce) * 100.0 / NULLIF(COUNT(*), 0) AS commerce_pct,
    AVG(b.views) FILTER (WHERE b.is_commerce) AS commerce_avg_views,
    AVG(b.views) FILTER (WHERE NOT b.is_commerce) AS organic_avg_views,
    COUNT(*) FILTER (WHERE b.dialect = 'southern') AS southern_count,
    COUNT(*) FILTER (WHERE b.dialect = 'northern') AS northern_count,
    COUNT(*) FILTER (WHERE b.cta_type IS NOT NULL) * 100.0 / NULLIF(COUNT(*), 0) AS has_cta_pct,
    COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags = TRUE) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.has_vietnamese_hashtags IS NOT NULL), 0) AS pct_has_specific_hashtags,
    COUNT(*) FILTER (WHERE b.has_caption_text = TRUE) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.has_caption_text IS NOT NULL), 0) AS pct_has_caption_text,
    AVG(b.hashtag_count) AS avg_hashtag_count,
    COUNT(*) FILTER (WHERE b.is_original_sound = TRUE) * 100.0 /
      NULLIF(COUNT(*) FILTER (WHERE b.is_original_sound IS NOT NULL), 0) AS pct_original_sound,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.scene_count) AS median_scene_count
  FROM base b
  GROUP BY b.content_class_id
)
SELECT
  a.content_class_id,
  a.sample_size,
  COALESCE(h.hook_distribution, '{}'::jsonb) AS hook_distribution,
  COALESCE(t.tone_distribution, '{}'::jsonb) AS tone_distribution,
  a.avg_face_appears_at,
  a.pct_face_in_half_sec,
  a.avg_transitions_per_second,
  a.avg_duration,
  a.median_duration,
  a.min_duration,
  a.max_duration,
  a.avg_engagement_rate,
  a.median_er,
  a.median_views,
  a.p50_views,
  a.avg_views,
  a.avg_text_overlays,
  a.commerce_pct,
  a.commerce_avg_views,
  a.organic_avg_views,
  a.southern_count,
  a.northern_count,
  a.has_cta_pct,
  a.pct_has_specific_hashtags,
  a.pct_has_caption_text,
  a.avg_hashtag_count,
  a.pct_original_sound,
  a.median_scene_count,
  CASE
    WHEN a.sample_size >= 50 THEN 'strong'
    WHEN a.sample_size >= 30 THEN 'moderate'
    WHEN a.sample_size >= 10 THEN 'early'
    ELSE 'thin'
  END AS claim_tier,
  NOW() AS computed_at
FROM agg a
LEFT JOIN hook_dist h ON h.content_class_id = a.content_class_id
LEFT JOIN tone_dist t ON t.content_class_id = a.content_class_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_class_intelligence_pk
  ON content_class_intelligence(content_class_id);

GRANT SELECT ON content_class_intelligence TO authenticated;

CREATE MATERIALIZED VIEW content_class_tier_intelligence AS
WITH base AS (
  SELECT content_class_id, creator_tier, views, engagement_rate
  FROM video_corpus
  WHERE indexed_at > NOW() - interval '30 days'
    AND language = 'vi'
    AND views > 0
    AND content_class_id IS NOT NULL
    AND creator_tier IS NOT NULL
)
SELECT
  b.content_class_id,
  b.creator_tier,
  COUNT(*) AS sample_size,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.views) AS median_views,
  PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY b.views) AS p75_views,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY b.engagement_rate) AS median_er,
  AVG(b.views) AS avg_views,
  AVG(b.engagement_rate) AS avg_engagement_rate,
  NOW() AS computed_at
FROM base b
GROUP BY b.content_class_id, b.creator_tier;

CREATE UNIQUE INDEX IF NOT EXISTS idx_content_class_tier_intelligence_pk
  ON content_class_tier_intelligence (content_class_id, creator_tier);

GRANT SELECT ON content_class_tier_intelligence TO authenticated;

-- ── Drop niche_id indexes on video_corpus ───────────────────────────────────
DROP INDEX IF EXISTS public.idx_corpus_niche_date;
DROP INDEX IF EXISTS public.idx_corpus_niche_er;
DROP INDEX IF EXISTS public.idx_video_corpus_niche_views;
DROP INDEX IF EXISTS public.idx_corpus_hook_type;
DROP INDEX IF EXISTS public.idx_corpus_face_timing;
DROP INDEX IF EXISTS public.idx_corpus_tone;
DROP INDEX IF EXISTS public.idx_corpus_first_frame;
DROP INDEX IF EXISTS public.idx_corpus_duration;
DROP INDEX IF EXISTS public.idx_corpus_format;
DROP INDEX IF EXISTS public.idx_corpus_commerce;
DROP INDEX IF EXISTS public.idx_corpus_save_rate;
DROP INDEX IF EXISTS public.idx_corpus_posting_hour;
DROP INDEX IF EXISTS public.idx_corpus_creator_tier;
DROP INDEX IF EXISTS public.idx_corpus_breakout;
DROP INDEX IF EXISTS public.idx_corpus_breakout_ratio;
DROP INDEX IF EXISTS public.idx_corpus_organic;
DROP INDEX IF EXISTS public.idx_corpus_specific_hashtags;
DROP INDEX IF EXISTS public.idx_corpus_caption_text;

-- ── Drop FK + column ────────────────────────────────────────────────────────
ALTER TABLE public.video_corpus
  DROP CONSTRAINT IF EXISTS video_corpus_niche_id_fkey;

ALTER TABLE public.video_corpus
  DROP COLUMN IF EXISTS niche_id;

COMMIT;
