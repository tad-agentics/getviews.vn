-- A.2.2 (two-axis deep pivot, 2026-05-15) — content_class_hook_effectiveness.
--
-- Parallel to ``hook_effectiveness`` but keyed on
-- ``content_classifications.id`` instead of ``niche_taxonomy.id``.
-- Lets pattern thesis / video diagnosis rank hooks at the (topic ×
-- format) granularity once A.2.3 plumbs the read paths through.
--
-- ── Why a parallel table (not dual-keyed) ───────────────────────────
--
-- A single table with both ``niche_id`` and ``content_class_id``
-- nullable would require partial unique indexes (since NULL is treated
-- as distinct in regular UNIQUE constraints), which Supabase PostgREST
-- ``upsert(on_conflict=...)`` doesn't support cleanly. A parallel
-- table keeps the existing UNIQUE(niche_id, hook_type) intact and
-- gives the new compute path its own simple UNIQUE(content_class_id,
-- hook_type). Read layer (A.2.3) queries both as needed.
--
-- ── Schema mirrors hook_effectiveness ───────────────────────────────
--
-- Same columns + computed_at semantics so consumers can treat both
-- tables interchangeably (PR3 introduces a fetcher that picks the
-- right table based on grouping axis).
--
-- ── Idempotency ─────────────────────────────────────────────────────
--
-- CREATE TABLE IF NOT EXISTS + ADD CONSTRAINT IF NOT EXISTS — safe
-- to re-run.

CREATE TABLE IF NOT EXISTS content_class_hook_effectiveness (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_class_id INTEGER NOT NULL REFERENCES content_classifications(id) ON DELETE CASCADE,
  hook_type TEXT NOT NULL,
  avg_views BIGINT,
  avg_engagement_rate NUMERIC(10, 4),
  avg_completion_rate NUMERIC(10, 4),
  sample_size INTEGER,
  trend_direction TEXT CHECK (trend_direction IN ('rising', 'stable', 'declining')),
  computed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_content_class_hook_effectiveness_class
  ON content_class_hook_effectiveness (content_class_id, computed_at DESC);

ALTER TABLE content_class_hook_effectiveness ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users read content_class_hook_effectiveness"
  ON content_class_hook_effectiveness;

CREATE POLICY "Authenticated users read content_class_hook_effectiveness"
  ON content_class_hook_effectiveness FOR SELECT
  TO authenticated
  USING (auth.uid() IS NOT NULL);

-- Required for upsert(on_conflict="content_class_id,hook_type")
-- in hook_effectiveness_compute.run_hook_effectiveness.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'content_class_hook_effectiveness_class_hook_unique'
  ) THEN
    ALTER TABLE content_class_hook_effectiveness
      ADD CONSTRAINT content_class_hook_effectiveness_class_hook_unique
      UNIQUE (content_class_id, hook_type);
  END IF;
END $$;
