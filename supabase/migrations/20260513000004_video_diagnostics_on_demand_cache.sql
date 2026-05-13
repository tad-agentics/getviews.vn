-- Enable on-demand video diagnoses to use the existing video_diagnostics
-- cache. Previously the table had a hard FK to video_corpus, so
-- on-demand analyses (TikTok URLs not in corpus, e.g. anything from
-- curnon.official which has zero corpus rows) could not be cached.
-- Every paste of the same URL paid the full 6+ minute video-extraction
-- pipeline cost: EnsembleData fetch → CDN download → Gemini Files API
-- upload + ACTIVE poll → frame extraction.
--
-- Production data (2026-05-12 → 2026-05-13): one user retried the same
-- non-corpus video 7× in one hour, paying ~7 minutes of compute each
-- time. With this cache, the second-and-subsequent requests within
-- the 1h TTL skip Gemini entirely and serve from the row already
-- written by the first run.
--
-- Schema changes:
--   1. Drop the FK to video_corpus.video_id (was ON DELETE CASCADE).
--      Existing corpus-path behaviour is unchanged — the upsert is
--      still keyed by video_id; the FK was only structurally
--      preventing on-demand insertions.
--   2. Add `source` to distinguish corpus vs on-demand rows.
--      Defaults to 'corpus' so existing rows are correctly labelled.
--   3. Add `tiktok_url` so on-demand reads can short-circuit on URL
--      alone, avoiding the EnsembleData round-trip needed to resolve
--      URL → aweme_id.

ALTER TABLE video_diagnostics
  DROP CONSTRAINT IF EXISTS video_diagnostics_video_id_fkey;

ALTER TABLE video_diagnostics
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'corpus'
    CHECK (source IN ('corpus', 'on_demand')),
  ADD COLUMN IF NOT EXISTS tiktok_url TEXT,
  -- On-demand caches the full response as JSON because the meta block
  -- (creator/views/likes/etc.) and niche_meta come from EnsembleData
  -- + classification, not from corpus joins. Re-fetching them on a
  -- cache hit would defeat the purpose. corpus rows leave this NULL —
  -- they reconstruct via _response_from_diagnostics_row from the
  -- granular columns + the joined video_corpus row.
  ADD COLUMN IF NOT EXISTS cached_response JSONB;

CREATE INDEX IF NOT EXISTS idx_video_diagnostics_tiktok_url
  ON video_diagnostics (tiktok_url)
  WHERE tiktok_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_video_diagnostics_source_computed_at
  ON video_diagnostics (source, computed_at DESC);

COMMENT ON COLUMN video_diagnostics.source IS
  '''corpus'' rows are written by the corpus pipeline (FK-clean rows '
  'still referencing video_corpus by id). ''on_demand'' rows are '
  'written by run_video_analyze_on_demand for TikTok URLs not in '
  'corpus; readers may filter by source to scope retention policies.';

COMMENT ON COLUMN video_diagnostics.tiktok_url IS
  'Populated only on on-demand rows. Enables the read path to look up '
  'a cached analysis by URL alone (avoiding the EnsembleData URL→aweme '
  'fetch that costs ~4s).';
