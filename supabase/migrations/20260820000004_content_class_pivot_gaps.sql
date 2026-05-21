-- Content-class corpus pivot — gap closure: ACQE discovery flag + class trend velocity.

BEGIN;

ALTER TABLE acqe_run_state
  ADD COLUMN IF NOT EXISTS discovery_relax_active BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN acqe_run_state.discovery_relax_active IS
  'ACQE sets true when any class is Thin/Dormant — batch ingest widens discovery pool.';

CREATE TABLE IF NOT EXISTS content_class_trend_velocity (
  content_class_id INTEGER NOT NULL
    REFERENCES content_classifications(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  hook_type_shifts JSONB,
  new_hashtags TEXT[],
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (content_class_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_content_class_trend_velocity_week
  ON content_class_trend_velocity (week_start DESC);

ALTER TABLE content_class_trend_velocity ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated read content class trend velocity"
  ON content_class_trend_velocity;
CREATE POLICY "Authenticated read content class trend velocity"
  ON content_class_trend_velocity
  FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS "Service role manages content class trend velocity"
  ON content_class_trend_velocity;
CREATE POLICY "Service role manages content class trend velocity"
  ON content_class_trend_velocity
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

GRANT SELECT ON content_class_trend_velocity TO authenticated;
GRANT ALL ON content_class_trend_velocity TO service_role;

COMMIT;
