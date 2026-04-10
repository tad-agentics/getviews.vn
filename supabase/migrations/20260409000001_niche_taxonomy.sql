-- niche_taxonomy — reference niches (read for all, no client writes)

CREATE TABLE niche_taxonomy (
  id SERIAL PRIMARY KEY,
  name_vn TEXT NOT NULL UNIQUE,
  name_en TEXT NOT NULL,
  signal_hashtags TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE niche_taxonomy ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read niche taxonomy"
  ON niche_taxonomy FOR SELECT
  TO anon, authenticated
  USING (true);

-- No INSERT/UPDATE/DELETE for clients (service_role bypasses RLS for batch jobs if needed)
