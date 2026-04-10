-- N-14: Change profiles.primary_niche from TEXT to INTEGER FK → niche_taxonomy.id
-- Existing TEXT values are cast to integer (they were stored as numeric strings via parseInt).
-- Rows with non-numeric or null values are set to null.

ALTER TABLE profiles
  ALTER COLUMN primary_niche TYPE integer
  USING CASE
    WHEN primary_niche ~ '^\d+$' THEN primary_niche::integer
    ELSE NULL
  END;

ALTER TABLE profiles
  ADD CONSTRAINT fk_profiles_primary_niche
  FOREIGN KEY (primary_niche) REFERENCES niche_taxonomy(id) ON DELETE SET NULL;
