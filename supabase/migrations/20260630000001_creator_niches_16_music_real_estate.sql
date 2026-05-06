-- ISSUE-011 — Expand UX-facing ``creator_niches`` from 14 → 16 buckets.
--
--   15 ``music_dance``   — Âm nhạc · Vũ đạo (content classes 28–29 were
--      primary under Comedy; they move here as the canonical home).
--   16 ``real_estate``   — Bất động sản · Nhà đất (class 51 moves from
--      Business as canonical home; legacy niche_taxonomy id=10 maps here).
--
-- ``map_legacy_niche_to_creator_niche`` is updated so backfills / SQL
-- callers align with ``src/lib/profileNiches.ts`` + Cloud Run
-- ``profile_niches.py``.
--
-- Version ``20260630000001`` (not ``…000000``) — remote already has
-- ``20260630000000_drop_primary_niche_sync_trigger_pr6.sql`` in
-- ``schema_migrations``; Supabase uses one row per numeric prefix.

BEGIN;

INSERT INTO creator_niches (id, slug, name_vn, name_en, description_vn, display_order) VALUES
  (15, 'music_dance', 'Âm nhạc · Vũ đạo', 'Music & Dance',
       'Cover hát, nhạc cụ, dance challenge, choreography, sân khấu K-pop.', 52),
  (16, 'real_estate', 'Bất động sản · Nhà đất', 'Real Estate',
       'Tour căn hộ, review dự án, môi giới, tư vấn mua bán, listing nhà đất.', 95)
ON CONFLICT (id) DO UPDATE SET
  slug = EXCLUDED.slug,
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  description_vn = EXCLUDED.description_vn,
  display_order = EXCLUDED.display_order,
  active = TRUE;

-- Move music/dance content classes to creator_niche 15 (canonical).
DELETE FROM creator_niche_content_classes
WHERE creator_niche_id = 5 AND content_class_id IN (28, 29);

DELETE FROM creator_niche_content_classes
WHERE creator_niche_id = 9 AND content_class_id = 51;

INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary) VALUES
  (15, 28, TRUE),
  (15, 29, TRUE),
  (16, 51, TRUE)
ON CONFLICT (creator_niche_id, content_class_id) DO UPDATE SET
  is_primary = EXCLUDED.is_primary;

SELECT setval(
  'creator_niches_id_seq',
  GREATEST(16, (SELECT COALESCE(MAX(id), 1) FROM creator_niches))
);

CREATE OR REPLACE FUNCTION map_legacy_niche_to_creator_niche(legacy_id INTEGER)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT CASE legacy_id
    WHEN 1  THEN 9   -- Shopee review (retired) → Business & Finance
    WHEN 2  THEN 1   -- Skincare → Beauty
    WHEN 3  THEN 2   -- Thời trang → Fashion
    WHEN 4  THEN 3   -- Food → Food
    WHEN 5  THEN 9   -- Kinh doanh online → Business & Finance
    WHEN 6  THEN 4   -- Chị đẹp (retired) → Lifestyle (was aspirational)
    WHEN 7  THEN 6   -- Mẹ bỉm → Family
    WHEN 8  THEN 14  -- Gym / Fitness VN → Gym & Fitness
    WHEN 9  THEN 8   -- Tech → Tech & Gaming
    WHEN 10 THEN 16  -- Bất động sản → Real Estate (creator_niche 16)
    WHEN 11 THEN 7   -- EduTok → Education
    WHEN 12 THEN 9   -- Livestream (retired) → Business & Finance
    WHEN 13 THEN 5   -- Hài → Comedy
    WHEN 14 THEN 12  -- Auto/Moto → Auto & Moto
    WHEN 15 THEN 9   -- Tài chính → Business & Finance
    WHEN 16 THEN 11  -- Travel → Travel & Outdoor Sports
    WHEN 17 THEN 8   -- Gaming → Tech & Gaming
    WHEN 18 THEN 3   -- Nấu ăn (retired) → Food
    WHEN 19 THEN 13  -- Pets → Pets & Home
    WHEN 20 THEN 13  -- Home decor → Pets & Home
    WHEN 21 THEN 11  -- Sports → Travel & Outdoor Sports
    WHEN 22 THEN 15  -- K-pop (retired) → Music & Dance
    WHEN 23 THEN 7   -- Language (retired) → Education
    WHEN 24 THEN 9   -- Crypto (retired) → Business & Finance
    WHEN 25 THEN 12  -- Moto culture (retired) → Auto & Moto
    WHEN 26 THEN 10  -- Wellness → Wellness & Health
    ELSE NULL
  END;
$$;

COMMIT;
