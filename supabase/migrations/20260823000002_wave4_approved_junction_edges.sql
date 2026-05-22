-- Wave 4 — approved secondary junction edges from two-axis-niche-model.md §9 triage.
-- is_primary=FALSE — does not override primary tie-break; fixes junction-invalid
-- corpus rows where Gemini cross-bucket assignment is intentional.

BEGIN;

INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
VALUES
  (9, 51, FALSE),  -- business → real_estate_listing (5 rows)
  (9, 73, FALSE),  -- business → home_decor_inspiration (3 rows)
  (4, 49, FALSE),  -- lifestyle → ecommerce_shopee_review (3 rows)
  (9, 49, FALSE),  -- business → ecommerce_shopee_review (affiliate overlap)
  (4, 73, FALSE),  -- lifestyle → home_decor_inspiration (decor vlog overlap)
  (16, 51, FALSE)  -- real_estate → real_estate_listing (explicit primary niche)
ON CONFLICT (creator_niche_id, content_class_id) DO NOTHING;

COMMIT;
