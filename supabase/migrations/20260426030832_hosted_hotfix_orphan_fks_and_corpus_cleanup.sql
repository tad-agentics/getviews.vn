-- Hosted hotfix applied 2026-04-26 03:08:32 (version recorded in
-- supabase_migrations only; this file aligns repo replay with prod).
--
-- Context: ``competitor_tracking``, ``creator_pattern``, ``push_events`` existed
-- in prod before 20260504000000_adopt_orphan_tables. This migration:
--   1) Drops video_corpus comment_radar / thumbnail_analysis cache columns (and
--      their partial indexes) that were added earlier in the chain — prod chose
--      to remove them at this point; 20260528000001 restores them for pipeline.
--   2) Re-points orphan-table user_id FKs from auth.users to public.profiles(id).
--   3) Relaxes push_events delivery flags to nullable (matches dashboard-era rows).
--
-- On a fresh replay, orphan tables may not exist yet — FK/push_events blocks are
-- guarded. video_corpus always exists by this timestamp.

DROP INDEX IF EXISTS public.video_corpus_comment_radar_fetched_idx;
DROP INDEX IF EXISTS public.video_corpus_thumbnail_fetched_idx;

ALTER TABLE public.video_corpus
  DROP COLUMN IF EXISTS comment_radar,
  DROP COLUMN IF EXISTS comment_radar_fetched_at,
  DROP COLUMN IF EXISTS thumbnail_analysis,
  DROP COLUMN IF EXISTS thumbnail_analysis_fetched_at;

DO $body$
BEGIN
  IF to_regclass('public.competitor_tracking') IS NOT NULL THEN
    ALTER TABLE public.competitor_tracking
      DROP CONSTRAINT IF EXISTS competitor_tracking_user_id_fkey;
    ALTER TABLE public.competitor_tracking
      ADD CONSTRAINT competitor_tracking_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES public.profiles (id);
  END IF;

  IF to_regclass('public.creator_pattern') IS NOT NULL THEN
    ALTER TABLE public.creator_pattern
      DROP CONSTRAINT IF EXISTS creator_pattern_user_id_fkey;
    ALTER TABLE public.creator_pattern
      ADD CONSTRAINT creator_pattern_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES public.profiles (id);
  END IF;

  IF to_regclass('public.push_events') IS NOT NULL THEN
    ALTER TABLE public.push_events
      DROP CONSTRAINT IF EXISTS push_events_user_id_fkey;
    ALTER TABLE public.push_events
      ADD CONSTRAINT push_events_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES public.profiles (id);
    ALTER TABLE public.push_events
      ALTER COLUMN sent_email DROP NOT NULL;
    ALTER TABLE public.push_events
      ALTER COLUMN sent_inapp DROP NOT NULL;
  END IF;
END;
$body$;
