-- Phase 0b — hashtag_class_map (class-scoped discovery; learn loop in Phase 3).

BEGIN;

CREATE TABLE IF NOT EXISTS hashtag_class_map (
  hashtag TEXT NOT NULL,
  content_class_id INTEGER NOT NULL
    REFERENCES content_classifications(id) ON DELETE CASCADE,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  yield_14d DOUBLE PRECISION,
  last_seen_at TIMESTAMPTZ,
  source TEXT NOT NULL DEFAULT 'batch_learn',
  occurrences INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (hashtag, content_class_id)
);

CREATE INDEX IF NOT EXISTS idx_hashtag_class_map_class
  ON hashtag_class_map (content_class_id);

CREATE INDEX IF NOT EXISTS idx_hashtag_class_map_yield
  ON hashtag_class_map (content_class_id, yield_14d DESC NULLS LAST)
  WHERE yield_14d IS NOT NULL;

ALTER TABLE hashtag_class_map ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages hashtag class map" ON hashtag_class_map;
CREATE POLICY "Service role manages hashtag class map"
  ON hashtag_class_map
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Authenticated read hashtag class map" ON hashtag_class_map;
CREATE POLICY "Authenticated read hashtag class map"
  ON hashtag_class_map
  FOR SELECT
  TO authenticated
  USING (true);

GRANT SELECT ON hashtag_class_map TO authenticated;
GRANT ALL ON hashtag_class_map TO service_role;

COMMENT ON TABLE hashtag_class_map IS
  'Hashtag → content_class_id map v2. Spec: artifacts/docs/hashtag-class-map-v2.md';

COMMIT;
