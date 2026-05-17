-- Phase 1 of the Layer 0 simplification — sunset Module 0C.
--
-- Module 0C (cross-niche format migration) was a weekly Gemini call that
-- inspected the hook×format distribution across all niches and wrote a JSON
-- list of migrations into `niche_insights.cross_niche_signals`. The column
-- has NEVER been read by anyone — no frontend, no other cloud-run module,
-- no Edge Function, no SQL view, no RLS policy. Confirmed via:
--
--   - rg 'cross_niche_signals' src/  api/  supabase/functions/   → 0 hits
--   - rg 'cross_niche_signals' cloud-run/                        → only the
--     now-deleted writer (layer0_migration.py) and this column's seed
--     comment in 20260414000031_create_niche_insights.sql
--   - pg_views / pg_matviews / pg_proc / pg_policy LIKE '%cross_niche_signals%'
--     → 0 rows (2026-05-17)
--
-- 8 of 78 lifetime rows ever populated this column (10%). Pure write-only
-- column; safe to drop along with the writer.
--
-- The writer (cloud-run/getviews_pipeline/layer0_migration.py), its prompt
-- template + schema in layer0_prompts.py, and the call sites in
-- corpus_ingest.py, routers/batch.py, routers/admin.py are all removed in
-- the same commit as this migration.

ALTER TABLE public.niche_insights
  DROP COLUMN IF EXISTS cross_niche_signals;

-- Rollback (recreate as nullable JSONB; new rows will write NULL since the
-- writer is gone — keep the writer-removal commit reverted too):
--
--   ALTER TABLE public.niche_insights
--     ADD COLUMN cross_niche_signals JSONB;
