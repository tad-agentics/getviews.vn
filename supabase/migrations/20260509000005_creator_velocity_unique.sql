-- 2026-05-09 — add UNIQUE(creator_handle, niche_id) on creator_velocity.
--
-- Required for ``batch_analytics._upsert_creator_velocity_sync`` which
-- upserts via ``on_conflict="creator_handle,niche_id"``. Without this
-- constraint, the PostgREST upsert path returns 42P10:
--
--   "there is no unique or exclusion constraint matching the
--    ON CONFLICT specification"
--
-- Result: every /batch/analytics run fails on the creator_velocity
-- pass — creators_updated=0, videos_updated=0 — so
-- breakout_multiplier never gets computed on video_corpus rows. This
-- is the same class of bug fixed for hook_effectiveness by
-- 20260509000000_hook_effectiveness_unique.sql.
--
-- Verified 2026-05-09 via live DB: ``creator_velocity`` has 0 rows
-- (upsert has never succeeded) and 0 duplicate (handle, niche_id)
-- pairs, so the DDL is guaranteed to succeed on apply.

ALTER TABLE public.creator_velocity
  ADD CONSTRAINT creator_velocity_handle_niche_unique
  UNIQUE (creator_handle, niche_id);
