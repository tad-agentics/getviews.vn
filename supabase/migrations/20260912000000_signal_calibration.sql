-- Calibration loop v1 (2026-06-14) — append-only signal_calibration +
-- signal_predictive_value tables.
--
-- PostgREST upsert(on_conflict=...) cannot use partial unique indexes
-- (see content_class_hook_effectiveness migration note). Jobs INSERT
-- one row per scope/class per run; readers select latest by computed_at.

CREATE TABLE IF NOT EXISTS signal_calibration (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope TEXT NOT NULL CHECK (scope IN ('global', 'content_class')),
  content_class_id INTEGER REFERENCES content_classifications(id) ON DELETE CASCADE,
  w_hook NUMERIC(6, 4) NOT NULL,
  w_format NUMERIC(6, 4) NOT NULL,
  w_time NUMERIC(6, 4) NOT NULL,
  rho_holdout NUMERIC(8, 4) NOT NULL,
  rho_baseline NUMERIC(8, 4) NOT NULL,
  sample_size INTEGER NOT NULL,
  adopted BOOLEAN NOT NULL DEFAULT false,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_calibration_latest
  ON signal_calibration (scope, content_class_id, computed_at DESC);

ALTER TABLE signal_calibration ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users read signal_calibration"
  ON signal_calibration;

CREATE POLICY "Authenticated users read signal_calibration"
  ON signal_calibration FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

CREATE TABLE IF NOT EXISTS signal_predictive_value (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_type TEXT NOT NULL,
  content_class_id INTEGER REFERENCES content_classifications(id) ON DELETE CASCADE,
  predictive_rho NUMERIC(8, 4) NOT NULL,
  sample_size INTEGER NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_predictive_value_latest
  ON signal_predictive_value (signal_type, content_class_id, computed_at DESC);

ALTER TABLE signal_predictive_value ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users read signal_predictive_value"
  ON signal_predictive_value;

CREATE POLICY "Authenticated users read signal_predictive_value"
  ON signal_predictive_value FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);
