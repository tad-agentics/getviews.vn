-- Phase A validation — daily_ritual + pulse + starter_creators + onboarding funnel.
--
-- Paste into Supabase SQL Editor in order. Each section prints expected vs
-- observed so you can eyeball "are we healthy?" in one pass.
--
-- Source of truth for what should exist:
--   supabase/migrations/20260423000049_phase_a_reference_channels.sql
--   supabase/migrations/20260423000050_daily_ritual.sql
--
-- Report all-SQL results back in the checkout conversation; I'll interpret.

-- ─────────────────────────────────────────────────────────────────────────
-- 1. Migrations applied? (should print 2 rows)
-- ─────────────────────────────────────────────────────────────────────────
SELECT version, name
FROM supabase_migrations.schema_migrations
WHERE name IN ('phase_a_reference_channels', 'daily_ritual')
ORDER BY version;

-- 2. Schema shape — columns exist where we expect them.
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE (table_name = 'profiles' AND column_name = 'reference_channel_handles')
   OR (table_name = 'starter_creators')
   OR (table_name = 'daily_ritual')
ORDER BY table_name, ordinal_position;


-- ─────────────────────────────────────────────────────────────────────────
-- 3. starter_creators — did seed_starter_creators(10) actually populate?
--    One row per (niche_id, handle), ≤ 10 per niche.
-- ─────────────────────────────────────────────────────────────────────────
SELECT
  niche_id,
  COUNT(*)                         AS seeded_count,
  MIN(rank)                        AS min_rank,
  MAX(rank)                        AS max_rank,
  BOOL_OR(is_curated)              AS any_curated,
  MAX(last_seeded_at)              AS last_seeded
FROM starter_creators
GROUP BY niche_id
ORDER BY niche_id;
-- Expected: one row per niche that had ≥1 creator in video_corpus. Zero-seed
-- niches simply don't appear. `any_curated` should be FALSE across the board
-- unless someone manually flagged rows.


-- ─────────────────────────────────────────────────────────────────────────
-- 4. daily_ritual — did the nightly batch write anything?
-- ─────────────────────────────────────────────────────────────────────────
SELECT
  generated_for_date,
  COUNT(*)                                 AS rows,
  COUNT(DISTINCT user_id)                  AS distinct_users,
  COUNT(DISTINCT niche_id)                 AS niches_covered,
  MIN(generated_at)                        AS first_write,
  MAX(generated_at)                        AS last_write
FROM daily_ritual
WHERE generated_for_date >= current_date - INTERVAL '7 days'
GROUP BY generated_for_date
ORDER BY generated_for_date DESC;
-- Expected: at least one row for TODAY (in UTC). Zero for today → cron
-- didn't run, or the batch ran but no user had a thick-enough corpus.

-- 5. Adequacy distribution across today's rituals.
SELECT adequacy, COUNT(*)
FROM daily_ritual
WHERE generated_for_date = current_date
GROUP BY adequacy
ORDER BY COUNT(*) DESC;
-- Expected: mostly `niche_norms` or higher. If most rows are `none` /
-- `reference_pool`, the corpus is too thin to generate honest scripts —
-- check corpus-health.

-- 6. Ritual hook-type diversity — are the 3 scripts actually distinct?
--    Counts rows whose scripts[] array contains < 3 distinct hook_type_en.
WITH ritual_hooks AS (
  SELECT
    user_id,
    generated_for_date,
    COUNT(DISTINCT s->>'hook_type_en') AS distinct_hooks,
    JSONB_ARRAY_LENGTH(scripts)         AS n_scripts
  FROM daily_ritual r, JSONB_ARRAY_ELEMENTS(r.scripts) s
  WHERE generated_for_date = current_date
  GROUP BY user_id, generated_for_date, scripts
)
SELECT
  COUNT(*) FILTER (WHERE distinct_hooks = 3)  AS diverse_rows,
  COUNT(*) FILTER (WHERE distinct_hooks < 3)  AS collapsed_rows,
  COUNT(*) FILTER (WHERE n_scripts <> 3)      AS wrong_length,
  COUNT(*)                                    AS total
FROM ritual_hooks;
-- Expected: diverse_rows == total. collapsed_rows > 0 means Gemini
-- returned duplicates; code drops them but the row isn't written
-- (so this query shouldn't surface many). wrong_length should be 0.

-- 7. Spot-check a ritual — latest row for the first active user.
--    Read the title_vi + why_works by eye. Are they shootable?
SELECT
  dr.user_id,
  p.display_name,
  dr.generated_for_date,
  dr.adequacy,
  CARDINALITY(dr.grounded_video_ids)  AS grounded_n,
  JSONB_PRETTY(dr.scripts)            AS scripts
FROM daily_ritual dr
JOIN profiles p ON p.id = dr.user_id
WHERE dr.generated_for_date = (SELECT MAX(generated_for_date) FROM daily_ritual)
ORDER BY dr.generated_at DESC
LIMIT 1;


-- ─────────────────────────────────────────────────────────────────────────
-- 8. Onboarding funnel — who has each step done?
-- ─────────────────────────────────────────────────────────────────────────
SELECT
  COUNT(*)                                                           AS total_users,
  COUNT(*) FILTER (WHERE primary_niche IS NOT NULL)                  AS step_1_niche_set,
  COUNT(*) FILTER (WHERE
      primary_niche IS NOT NULL
      AND CARDINALITY(reference_channel_handles) > 0
  )                                                                  AS step_2_references_set,
  COUNT(*) FILTER (WHERE
      primary_niche IS NOT NULL
      AND CARDINALITY(reference_channel_handles) BETWEEN 1 AND 3
  )                                                                  AS step_2_within_cap
FROM profiles;
-- Expected: step_2 ≤ step_1 ≤ total_users.
-- step_2_within_cap < step_2_references_set means the CHECK constraint
-- isn't doing its job (shouldn't be possible given the migration).


-- ─────────────────────────────────────────────────────────────────────────
-- 9. Corpus depth per niche (explains thin-corpus rituals).
-- ─────────────────────────────────────────────────────────────────────────
SELECT
  t.id                                                         AS niche_id,
  COALESCE(t.name_vn, t.name_en)                               AS niche,
  COUNT(*) FILTER (WHERE v.created_at >= now() - interval  '7 days') AS videos_7d,
  COUNT(*) FILTER (WHERE v.created_at >= now() - interval '30 days') AS videos_30d,
  MAX(v.created_at)                                            AS last_ingest_at
FROM   niche_taxonomy t
LEFT JOIN video_corpus v ON v.niche_id = t.id
GROUP BY t.id, t.name_vn, t.name_en
ORDER BY videos_7d DESC;
-- If videos_7d < 10 (MIN_GROUNDING_VIDEOS), the ritual falls back to 30d;
-- if videos_30d < 10 the ritual is skipped (thin_corpus).
