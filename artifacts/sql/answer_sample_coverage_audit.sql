-- Phase C.0.3 — populate artifacts/docs/answer-sample-coverage.md niche × window table.
-- Run against production/staging with a role that can read video_corpus + niche_taxonomy.
-- Floors: Pattern 30, Ideas 60, Timing 80 (see phase-c-plan.md §C.0.3).

-- Example: row counts per niche for 7d / 14d / 30d rolling windows (indexed_at)
WITH niches AS (
  SELECT id, name_vn FROM public.niche_taxonomy ORDER BY id
),
counts AS (
  SELECT
    n.id AS niche_id,
    n.name_vn,
    COUNT(*) FILTER (WHERE v.indexed_at >= now() - interval '7 days') AS n_7d,
    COUNT(*) FILTER (WHERE v.indexed_at >= now() - interval '14 days') AS n_14d,
    COUNT(*) FILTER (WHERE v.indexed_at >= now() - interval '30 days') AS n_30d
  FROM niches n
  LEFT JOIN public.video_corpus v ON v.niche_id = n.id
  GROUP BY n.id, n.name_vn
)
SELECT
  niche_id,
  name_vn,
  n_7d,
  n_14d,
  n_30d,
  (n_7d >= 30) AS pattern_ok_7d,
  (n_7d >= 60) AS ideas_ok_7d,
  (n_7d >= 80) AS timing_ok_7d
FROM counts
ORDER BY niche_id;
