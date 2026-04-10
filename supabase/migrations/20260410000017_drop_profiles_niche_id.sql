-- Drop redundant niche_id column from profiles.
-- The frontend reads/writes primary_niche (INTEGER FK to niche_taxonomy) exclusively.
-- niche_id was added in error as a duplicate — never used by any client code.
ALTER TABLE profiles DROP COLUMN IF EXISTS niche_id;
