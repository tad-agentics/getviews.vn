-- Performance advisor fixes (audit 2026-06-10), high-value + zero-risk only.
--
-- Supabase performance advisor flagged: 2 unindexed FKs, 7 RLS init-plan
-- re-evaluations, ~45 unused indexes, 3 duplicate-permissive-policy tables.
-- This migration applies the two classes that are safe and worthwhile:
--   1. The unindexed FK on video_corpus (the big, nightly-written table).
--   2. The init-plan fix on the ONE authenticated-facing hot-path policy.
-- The small-table policy hints (ingest_targets/trend_velocity/hashtag_class_map
-- are tiny reference tables) and the unused-index drop list are documented in
-- artifacts/qa-reports/performance-audit-2026-06-10.md as backlog — rewriting
-- RLS role-scoping or dropping indexes for marginal gain on small/cold tables
-- is exactly the kind of change that causes an outage, so it needs a human.

-- 1. FK covering indexes -----------------------------------------------------
-- video_corpus is ~9K rows growing ~1K/week; an unindexed FK on the niche
-- resolver column slows joins and any niche_taxonomy/creator_niches mutation.
CREATE INDEX IF NOT EXISTS idx_video_corpus_inferred_creator_niche
  ON public.video_corpus (inferred_creator_niche_id)
  WHERE inferred_creator_niche_id IS NOT NULL;

-- corpus_ingest_queue.niche_id FK (table added 2026-06-10) — cheap, advisor-flagged.
CREATE INDEX IF NOT EXISTS idx_corpus_ingest_queue_niche
  ON public.corpus_ingest_queue (niche_id)
  WHERE niche_id IS NOT NULL;

-- 2. RLS init-plan: content_class_hook_effectiveness ------------------------
-- Read by authenticated clients on pattern-report builds; the per-row
-- re-evaluation of auth.uid() scales with (classes × hook_types). Wrapping in
-- a scalar subselect lets Postgres evaluate it once per query. Behaviour is
-- identical (still "any authenticated user may read").
ALTER POLICY "Authenticated users read content_class_hook_effectiveness"
  ON public.content_class_hook_effectiveness
  USING ((select auth.uid()) IS NOT NULL);

-- 3. Drop two verified-dead GIN indexes on video_corpus -------------------
-- idx_corpus_hashtags (array GIN, 536kB) and idx_corpus_topics (array GIN,
-- 2.5MB) have idx_scan=0 and — verified by grep — NO query uses an array
-- containment operator (@>, .cs(), .ov()) on these columns. The only reader
-- (_corpus_hashtags_for_class_sync) selects hashtags as a payload column
-- filtered by content_class_id (separately indexed). GIN maintenance runs on
-- every nightly bulk upsert, so these are pure write-amplification.
-- NOTE: the answer_sessions trgm search indexes are NOT dropped — they show
-- idx_scan=0 only because history search is unused in prod so far; the
-- search_history_union RPC needs them.
DROP INDEX IF EXISTS public.idx_corpus_hashtags;
DROP INDEX IF EXISTS public.idx_corpus_topics;
