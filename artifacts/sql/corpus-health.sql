-- corpus-health.sql — "morning coffee" corpus-adequacy check.
--
-- Paste into Supabase SQL Editor, bookmark it, run it whenever you want to
-- answer "which niches are statistically thick enough to make which claims?".
--
-- Thresholds mirror cloud-run/getviews_pipeline/claim_tiers.py (CLAIM_TIERS):
--   reference_pool     =   5  — safe to show 3 references without scraping bottom
--   basic_citation     =  20  — "feels representative" bar for generic niche talk
--   niche_norms        =  30  — binary features reach ~±10% precision
--   hook_effectiveness =  50  — 14 hook types × ≥5/bucket (relaxed)
--   trend_delta        = 100  — two weeks × ≥50 instances per week window
--
-- If you change these thresholds, update claim_tiers.py too — this query is a
-- human mirror of the endpoint, not the source of truth.

WITH corpus AS (
  SELECT
    niche_id,
    COUNT(*) FILTER (WHERE created_at >= now() - interval  '7 days') AS videos_7d,
    COUNT(*) FILTER (WHERE created_at >= now() - interval '30 days') AS videos_30d,
    COUNT(*) FILTER (WHERE created_at >= now() - interval '90 days') AS videos_90d,
    MAX(created_at) AS last_ingest_at
  FROM video_corpus
  WHERE created_at >= now() - interval '90 days'
  GROUP BY niche_id
),
patterns AS (
  SELECT
    nid AS niche_id,
    MAX(last_seen_at) AS last_pattern_at
  FROM video_patterns, unnest(niche_spread) AS nid
  WHERE is_active
  GROUP BY nid
)
SELECT
  t.id                                    AS niche_id,
  COALESCE(t.name_en, t.name_vn)          AS niche,
  COALESCE(c.videos_7d,  0)               AS videos_7d,
  COALESCE(c.videos_30d, 0)               AS videos_30d,
  COALESCE(c.videos_90d, 0)               AS videos_90d,
  c.last_ingest_at,
  p.last_pattern_at,
  -- Highest claim tier this niche currently passes
  CASE
    WHEN COALESCE(c.videos_30d, 0) >= 100 THEN 'trend_delta'
    WHEN COALESCE(c.videos_30d, 0) >=  50 THEN 'hook_effectiveness'
    WHEN COALESCE(c.videos_30d, 0) >=  30 THEN 'niche_norms'
    WHEN COALESCE(c.videos_30d, 0) >=  20 THEN 'basic_citation'
    WHEN COALESCE(c.videos_30d, 0) >=   5 THEN 'reference_pool'
    ELSE 'none'
  END                                     AS highest_passing_tier
FROM   niche_taxonomy t
LEFT JOIN corpus   c ON c.niche_id = t.id
LEFT JOIN patterns p ON p.niche_id = t.id
ORDER BY videos_30d DESC, niche_id;
