-- Content-class corpus pivot — observability SQL (Phase 0)
-- Run in Supabase SQL editor after migration 20260820000000.

-- Cross-Niche Migration Rate (7d) — alert if > 0.25
SELECT
  COUNT(*) FILTER (
    WHERE ingest_loop_niche_id IS DISTINCT FROM niche_id
  )::FLOAT / NULLIF(COUNT(*), 0) AS cross_niche_migration_rate,
  COUNT(*) AS rows_7d
FROM video_corpus
WHERE indexed_at > NOW() - INTERVAL '7 days'
  AND ingest_loop_niche_id IS NOT NULL;

-- By relaxation tier
SELECT
  ingest_relaxation_tier,
  COUNT(*) AS n,
  COUNT(*) FILTER (
    WHERE ingest_loop_niche_id IS DISTINCT FROM niche_id
  )::FLOAT / NULLIF(COUNT(*), 0) AS migration_rate
FROM video_corpus
WHERE indexed_at > NOW() - INTERVAL '7 days'
  AND ingest_loop_niche_id IS NOT NULL
GROUP BY ingest_relaxation_tier
ORDER BY ingest_relaxation_tier;

-- Top loop → stored niche pairs
SELECT
  ingest_loop_niche_id,
  niche_id AS stored_niche_id,
  COUNT(*) AS n
FROM video_corpus
WHERE indexed_at > NOW() - INTERVAL '7 days'
  AND ingest_loop_niche_id IS DISTINCT FROM niche_id
GROUP BY 1, 2
ORDER BY n DESC
LIMIT 20;

-- content_class sample vs niche_intelligence (30d)
SELECT
  cc.content_class_id,
  cci.sample_size AS class_sample_30d,
  ni.sample_size AS niche_sample_30d
FROM content_class_intelligence cci
JOIN content_classifications cc ON cc.id = cci.content_class_id
LEFT JOIN video_corpus vc ON vc.content_class_id = cci.content_class_id
LEFT JOIN niche_intelligence ni ON ni.niche_id = vc.niche_id
WHERE cci.sample_size < 30
ORDER BY cci.sample_size ASC
LIMIT 30;

-- Thin classes (ACQE)
SELECT content_class_id, viability_tier, daily_vpn, active
FROM content_class_ingest_targets
WHERE viability_tier IN ('Thin', 'Dormant')
ORDER BY viability_tier, content_class_id;

-- Score cohort mismatch rate
SELECT
  COUNT(*) FILTER (WHERE score_cohort_mismatch)::FLOAT / NULLIF(COUNT(*), 0) AS mismatch_rate,
  COUNT(*) AS n
FROM video_corpus
WHERE indexed_at > NOW() - INTERVAL '7 days';
