-- Two-axis niche refactor — PR6 of 6 (final cleanup).
--
-- Drops the legacy ``profiles.primary_niche`` column. PR3 backfilled
-- ``creator_niche_id`` for every populated row; PR5 pivoted Cloud Run
-- + FE reads to creator_niche_id. The dual-write in PR4 onboarding /
-- settings preserved primary_niche during the transition window for
-- safety; PR6 removes both the column and the dual-write.
--
-- Kept (intentional, NOT cleanup scope):
--   - ``niche_taxonomy`` table — ``video_corpus.niche_id`` still FKs
--     here. Downstream analysis (compute_pulse, pattern thesis,
--     hook_effectiveness, daily_ritual) still filters on niche_id.
--     Deep pivot to ``content_class_id``-only queries is future work.
--   - ``video_corpus.niche_id`` column — see above.
--   - ``video_corpus.content_class_id`` column (PR2) — populated at
--     ingest, ready when analysis pivots later.
--   - ``creator_niche_content_classes`` junction (PR1) — ready for
--     future cross-niche queries.
--   - ``map_legacy_niche_to_creator_niche()`` SQL function — kept
--     idempotent in case future cold-clone DBs need it for retrofit.
--
-- Idempotent: ``DROP COLUMN IF EXISTS``.

BEGIN;

-- The dependent FK constraint was added in 20260410000012; PostgreSQL
-- drops the constraint automatically when the column is dropped.
ALTER TABLE profiles
  DROP COLUMN IF EXISTS primary_niche;

COMMIT;
