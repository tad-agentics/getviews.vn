-- Sprint 8 — Reclassify ``video_corpus.niche_id`` where batch ingest stamped the
-- loop niche (keyword/hashtag pool) but caption + hook signal_hashtags clearly
-- point at another ``niche_taxonomy`` row. Does not change the ingest pipeline.
--
-- Rule (data-only backfill):
--   1. Explicit creator overrides for known fashion creators miscategorized under Skincare.
--   2. For all other rows: count ``niche_taxonomy.signal_hashtags`` substring hits
--      (case-insensitive) in ``caption`` and in ``analysis_json->hook_analysis->hook_phrase``.
--      If the highest-scoring niche differs from the current ``niche_id`` and its hit
--      count is **at least 2 greater** than the assigned niche’s hit count, update
--      ``niche_id`` and recompute ``content_class_id`` via PR2 helper.
--
-- Preserves rows (UPDATE only). Wrapped in one transaction.
--
-- Remove or supersede this migration’s effects in a future sprint only if you
-- add a conflicting global reclass policy — otherwise one-time backfill is safe
-- to leave in history.

BEGIN;

-- ── 1) Creator overrides (confirmed cross-niche accounts) ─────────────────
UPDATE public.video_corpus vc
SET
  niche_id = 3,
  content_class_id = map_legacy_corpus_to_content_class(3, vc.content_format)
WHERE LOWER(TRIM(BOTH FROM vc.creator_handle)) IN ('harry.nista', 'raindinh.official')
  AND vc.niche_id IS DISTINCT FROM 3;

-- ── 2) Signal-hashtag dominance (≥2 more hits than assigned niche) ───────────
WITH tag_norm AS (
  SELECT
    nt.id AS niche_id,
    LOWER(TRIM(LEADING '#' FROM TRIM(BOTH FROM u.tag))) AS tag
  FROM public.niche_taxonomy nt
  CROSS JOIN LATERAL unnest(COALESCE(nt.signal_hashtags, ARRAY[]::text[])) AS u(tag)
  WHERE u.tag IS NOT NULL AND TRIM(BOTH FROM u.tag) <> ''
),
vc_text AS (
  SELECT
    vc.video_id,
    vc.niche_id AS assigned_niche_id,
    LOWER(COALESCE(vc.caption, '')) AS cap_lower,
    LOWER(COALESCE(
      NULLIF(TRIM(BOTH FROM vc.hook_phrase), ''),
      NULLIF(TRIM(BOTH FROM vc.analysis_json #>> '{hook_analysis,hook_phrase}'), ''),
      ''
    )) AS hook_lower
  FROM public.video_corpus vc
),
hits AS (
  SELECT
    vt.video_id,
    vt.assigned_niche_id,
    tn.niche_id AS candidate_niche,
    SUM(
      CASE
        WHEN LENGTH(tn.tag) > 0 AND (
          vt.cap_lower LIKE '%' || tn.tag || '%'
          OR vt.hook_lower LIKE '%' || tn.tag || '%'
        )
        THEN 1
        ELSE 0
      END
    )::int AS hit_count
  FROM vc_text vt
  CROSS JOIN tag_norm tn
  GROUP BY vt.video_id, vt.assigned_niche_id, tn.niche_id
),
best_ranked AS (
  SELECT
    video_id,
    candidate_niche,
    hit_count,
    ROW_NUMBER() OVER (
      PARTITION BY video_id
      ORDER BY hit_count DESC, candidate_niche ASC
    ) AS rn
  FROM hits
),
best_row AS (
  SELECT video_id, candidate_niche AS best_niche, hit_count AS best_count
  FROM best_ranked
  WHERE rn = 1
),
assigned_hits AS (
  SELECT h.video_id, h.hit_count AS assigned_hit_count
  FROM hits h
  INNER JOIN public.video_corpus vc ON vc.video_id = h.video_id
    AND h.candidate_niche = vc.niche_id
),
reclass AS (
  SELECT
    br.video_id,
    br.best_niche AS new_niche_id
  FROM best_row br
  INNER JOIN public.video_corpus vc ON vc.video_id = br.video_id
  LEFT JOIN assigned_hits ah ON ah.video_id = br.video_id
  WHERE br.best_niche <> vc.niche_id
    AND br.best_count >= COALESCE(ah.assigned_hit_count, 0) + 2
)
UPDATE public.video_corpus vc
SET
  niche_id = r.new_niche_id,
  content_class_id = map_legacy_corpus_to_content_class(r.new_niche_id, vc.content_format)
FROM reclass r
WHERE vc.video_id = r.video_id;

COMMIT;
