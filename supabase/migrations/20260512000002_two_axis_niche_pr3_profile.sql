-- Two-axis niche refactor — PR3 of 6.
--
-- Adds ``profiles.creator_niche_id`` (FK → creator_niches) so the
-- user's UX-facing niche identity is decoupled from the legacy
-- ``primary_niche`` (which pointed at the now-fragmenting
-- niche_taxonomy). Backfills via ``map_legacy_niche_to_creator_niche()``
-- (seeded in PR1).
--
-- ── PR3 scope ────────────────────────────────────────────────────────
--
--   1. Add nullable ``profiles.creator_niche_id INTEGER FK``.
--   2. Backfill from ``primary_niche`` via the SQL helper from PR1
--      (handles every legacy niche id 1-26 incl. retired).
--   3. Add index on (creator_niche_id) for the morning-ritual cron's
--      "iterate every user" pass + admin queries.
--
-- Does NOT touch:
--   - Cloud Run code (still reads primary_niche — PR5 pivots reads to
--     creator_niche_id + content_class joins).
--   - FE onboarding / Settings (still uses primary_niche — PR4
--     rewires to creator_niches).
--   - ``primary_niche`` column (kept for compat — PR6 drops after
--     PR4-PR5 migrate callers).
--
-- ── Edge case: pre-onboarding profiles ────────────────────────────────
--
-- ``primary_niche`` can legitimately be NULL between signup and
-- onboarding completion (the layout guard redirects them to
-- /app/onboarding). The backfill leaves ``creator_niche_id`` NULL for
-- those rows; PR4 will write through both columns during the transition
-- so onboarding completion sets both consistently.
--
-- ── Idempotency ──────────────────────────────────────────────────────
--
-- ADD COLUMN IF NOT EXISTS + WHERE creator_niche_id IS NULL on the
-- backfill = safe to re-run.

BEGIN;

-- ── 1. Add column ────────────────────────────────────────────────────

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS creator_niche_id INTEGER
  REFERENCES creator_niches(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_profiles_creator_niche
  ON profiles(creator_niche_id)
  WHERE creator_niche_id IS NOT NULL;

COMMENT ON COLUMN profiles.creator_niche_id IS
  'UX-facing creator self-id (FK → creator_niches). Drives onboarding picker, Settings → Ngách, Trends default pill, sidebar "Ngách của bạn". Distinct from analysis groupings (video_corpus.content_class_id). PR6 will drop the legacy primary_niche column after PR4 (FE) + PR5 (analysis) migrate.';

-- ── 2. Backfill from primary_niche ───────────────────────────────────

UPDATE profiles
SET creator_niche_id = map_legacy_niche_to_creator_niche(primary_niche)
WHERE creator_niche_id IS NULL
  AND primary_niche IS NOT NULL;

COMMIT;
