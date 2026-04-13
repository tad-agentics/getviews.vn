-- hashtag_niche_map: auto-expanding hashtag→niche classification table.
--
-- Seed: populated from niche_taxonomy.signal_hashtags (static, curated).
-- Growth: batch indexing job upserts new hashtags observed in corpus videos,
--         but only when the niche is confirmed via "onboarding" or "topics"
--         sources (not via hashtag classification — avoids circular dependency).
--
-- Auto-promotion rules:
--   occurrences >= 10 → participates in classification (index covers this)
--   niche_count >= 3  → is_generic = true, excluded from classification
--   occurrences = 100 (seed) → always active from day 1
--   niche_count = 99  (generic seed) → never un-flagged

CREATE TABLE IF NOT EXISTS hashtag_niche_map (
  hashtag      text PRIMARY KEY,
  niche_id     int REFERENCES niche_taxonomy(id),  -- NULL for generic entries
  occurrences  int DEFAULT 1,
  niche_count  int DEFAULT 1,
  source       text DEFAULT 'corpus',  -- 'seed' | 'corpus'
  is_generic   boolean DEFAULT false,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

-- Partial index: only active, non-generic, sufficiently-observed hashtags.
-- classify_from_hashtags() queries this subset.
CREATE INDEX IF NOT EXISTS idx_hashtag_niche_active
  ON hashtag_niche_map (hashtag)
  WHERE is_generic = false AND occurrences >= 10;

ALTER TABLE hashtag_niche_map ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read" ON hashtag_niche_map
  FOR SELECT USING (true);

CREATE POLICY "Service write" ON hashtag_niche_map
  FOR ALL USING (auth.role() = 'service_role');

-- ── Seed: niche_taxonomy.signal_hashtags → hashtag_niche_map ────────────────
-- occurrences=100 → always active from day 1 without waiting for corpus growth.
-- ON CONFLICT DO NOTHING: re-running migration is safe.

INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
SELECT
  LOWER(TRIM(LEADING '#' FROM unnest(signal_hashtags))),
  id,
  100,  -- pre-activate
  1,
  'seed',
  false
FROM niche_taxonomy
ON CONFLICT (hashtag) DO NOTHING;

-- ── Seed: generic zero-signal hashtags ──────────────────────────────────────
-- niche_count=99 prevents these from ever being un-flagged by learning.

INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('fyp',           NULL, 0, 99, 'seed', true),
  ('foryou',        NULL, 0, 99, 'seed', true),
  ('foryoupage',    NULL, 0, 99, 'seed', true),
  ('foryourpage',   NULL, 0, 99, 'seed', true),
  ('fypage',        NULL, 0, 99, 'seed', true),
  ('fypシ',         NULL, 0, 99, 'seed', true),
  ('viral',         NULL, 0, 99, 'seed', true),
  ('viralvideo',    NULL, 0, 99, 'seed', true),
  ('viraltiktok',   NULL, 0, 99, 'seed', true),
  ('tiktokviral',   NULL, 0, 99, 'seed', true),
  ('trending',      NULL, 0, 99, 'seed', true),
  ('trendingtiktok',NULL, 0, 99, 'seed', true),
  ('trend',         NULL, 0, 99, 'seed', true),
  ('explore',       NULL, 0, 99, 'seed', true),
  ('tiktok',        NULL, 0, 99, 'seed', true),
  ('tiktokvietnam', NULL, 0, 99, 'seed', true),
  ('xyzbca',        NULL, 0, 99, 'seed', true),
  ('blowthisup',    NULL, 0, 99, 'seed', true),
  ('xuhuong',       NULL, 0, 99, 'seed', true),
  ('thinhhanh',     NULL, 0, 99, 'seed', true),
  ('hot',           NULL, 0, 99, 'seed', true),
  ('viral2026',     NULL, 0, 99, 'seed', true),
  ('trending2026',  NULL, 0, 99, 'seed', true)
ON CONFLICT (hashtag) DO UPDATE
  SET is_generic  = true,
      niche_count = 99;
