-- Layer 0A output: pre-computed mechanism insights per niche per week
CREATE TABLE IF NOT EXISTS niche_insights (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  niche_id INTEGER NOT NULL REFERENCES niche_taxonomy(id),
  week_of DATE NOT NULL,
  top_formula_hook TEXT,
  top_formula_format TEXT,
  insight_text TEXT,           -- Vietnamese "WHY" paragraphs (2-3 đoạn)
  mechanisms JSONB,            -- array of Mechanism objects from NicheInsightResponse
  cross_niche_signals JSONB,   -- populated by Module 0C run_cross_niche_migration
  execution_tip TEXT,
  staleness_risk TEXT,         -- ENUM-like: LOW | MEDIUM | HIGH
  quality_flag TEXT,           -- LOW if automated quality checks fail, NULL = ok
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (niche_id, week_of)
);

ALTER TABLE niche_insights ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read niche_insights"
  ON niche_insights
  FOR SELECT
  USING (TRUE);

-- Index for Layer 2 chat lookups (most recent insight for a niche)
CREATE INDEX IF NOT EXISTS idx_niche_insights_niche_week
  ON niche_insights (niche_id, week_of DESC);
