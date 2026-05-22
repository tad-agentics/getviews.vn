-- Taxonomy feedback fixes (2026-05-22 review):
-- 1. Rename format_axis comedy_observational → observational_relatable (decouple from class slug 26)
-- 2. Promote lifestyle primary home for absorbed comedy + pets/home classes (69–74, 24–27)

BEGIN;

UPDATE content_classifications
SET format_axis = 'observational_relatable'
WHERE format_axis = 'comedy_observational';

UPDATE creator_niche_content_classes
SET is_primary = TRUE
WHERE creator_niche_id = 4
  AND content_class_id IN (24, 25, 26, 27, 69, 70, 71, 72, 73, 74);

COMMIT;
