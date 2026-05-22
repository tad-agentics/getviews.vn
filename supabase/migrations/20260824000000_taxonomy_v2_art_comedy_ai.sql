-- Taxonomy v2 — Art & Craft UX niche, Comedy picker restore, AI workflow class.
-- Human gate 2026-05-22: A) art_craft id=17, B) comedy id=5 restore (4 classes),
-- C) ai_tool_workflow_tutorial primary tech_gaming + secondary business.

BEGIN;

-- ── 1. Legacy ingest buckets ─────────────────────────────────────────
INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES
  (
    13,
    'Hài · Giải trí',
    'comedy_entertainment',
    ARRAY[
      '#hai', '#haihuoc', '#comedy', '#cuoivoibui', '#sketch', '#sitcom',
      '#parody', '#skit', '#reactvideo', '#meme', '#hai che', '#do vai'
    ]
  ),
  (
    29,
    'Nghệ thuật · Thủ công',
    'art_craft',
    ARRAY[
      '#art', '#drawing', '#painting', '#handmade', '#craft', '#diyart',
      '#thucong', '#ve tranh', '#3dart', '#resinart', '#tu lam', '#handcraft'
    ]
  )
ON CONFLICT (id) DO UPDATE SET
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  signal_hashtags = EXCLUDED.signal_hashtags;

SELECT setval(
  'niche_taxonomy_id_seq',
  GREATEST(29, (SELECT COALESCE(MAX(id), 1) FROM niche_taxonomy))
);

-- ── 2. UX creator niches ─────────────────────────────────────────────
UPDATE creator_niches SET
  active = TRUE,
  name_vn = 'Hài · Giải trí',
  name_en = 'Comedy & Entertainment',
  description_vn = 'Hài skit, parody, react, POV hài quan sát.',
  display_order = 45
WHERE id = 5;

INSERT INTO creator_niches (id, slug, name_vn, name_en, description_vn, display_order, active)
VALUES (
  17,
  'art_craft',
  'Nghệ thuật · Thủ công',
  'Art & Craft',
  'Vẽ tranh, handmade, thêu, gốm, DIY nghệ thuật.',
  135,
  TRUE
)
ON CONFLICT (id) DO UPDATE SET
  slug = EXCLUDED.slug,
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  description_vn = EXCLUDED.description_vn,
  display_order = EXCLUDED.display_order,
  active = EXCLUDED.active;

SELECT setval(
  'creator_niches_id_seq',
  GREATEST(17, (SELECT COALESCE(MAX(id), 1) FROM creator_niches))
);

UPDATE creator_niches SET
  description_vn = 'Vlog, tâm sự, POV đời sống, self-improvement — hài/thú cưng có ngách riêng.'
WHERE id = 4;

-- ── 3. New content classes (80–82) ───────────────────────────────────
INSERT INTO content_classifications (id, slug, name_vn, name_en, format_axis, topic_axis, description_vn)
VALUES
  (
    80,
    'art_process_tutorial',
    'Quy trình làm nghệ thuật',
    'Art process tutorial',
    'tutorial',
    'art_craft',
    'Tutorial từng bước vẽ, tô, sculpt, resin, digital art process.'
  ),
  (
    81,
    'craft_handmade_montage',
    'Handmade montage',
    'Craft handmade montage',
    'montage_highlights',
    'art_craft',
    'Montage quá trình làm handmade, timelapse thêu/gốm/DIY art.'
  ),
  (
    82,
    'ai_tool_workflow_tutorial',
    'Workflow công cụ AI',
    'AI tool workflow tutorial',
    'tutorial',
    'ai_automation',
    'Hướng dẫn thực hành ChatGPT, Gemini, Midjourney, automation kiếm tiền — không phải review gadget.'
  )
ON CONFLICT (id) DO UPDATE SET
  slug = EXCLUDED.slug,
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  format_axis = EXCLUDED.format_axis,
  topic_axis = EXCLUDED.topic_axis,
  description_vn = EXCLUDED.description_vn;

SELECT setval(
  'content_classifications_id_seq',
  GREATEST(82, (SELECT COALESCE(MAX(id), 1) FROM content_classifications))
);

-- ── 4. Junction — comedy restore (primary 24–27) ─────────────────────
UPDATE creator_niche_content_classes
SET is_primary = FALSE
WHERE creator_niche_id = 4 AND content_class_id IN (24, 25, 26, 27);

INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
VALUES
  (5, 24, TRUE),
  (5, 25, TRUE),
  (5, 26, TRUE),
  (5, 27, TRUE),
  (4, 24, FALSE),
  (4, 25, FALSE),
  (4, 26, FALSE),
  (4, 27, FALSE)
ON CONFLICT (creator_niche_id, content_class_id) DO UPDATE SET
  is_primary = EXCLUDED.is_primary;

-- ── 5. Junction — art_craft (80–81 primary) ───────────────────────────
INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
VALUES
  (17, 80, TRUE),
  (17, 81, TRUE),
  (4, 80, FALSE),
  (4, 81, FALSE)
ON CONFLICT (creator_niche_id, content_class_id) DO UPDATE SET
  is_primary = EXCLUDED.is_primary;

-- ── 6. Junction — AI class (primary tech_gaming, secondary business) ─
INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
VALUES
  (8, 82, TRUE),
  (9, 82, FALSE)
ON CONFLICT (creator_niche_id, content_class_id) DO UPDATE SET
  is_primary = EXCLUDED.is_primary;

-- ── 7. Carousel HI-16 grid for comedy (5) + art_craft (17) ───────────
INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
SELECT cn.id, cc.id, TRUE
FROM creator_niches cn
CROSS JOIN content_classifications cc
WHERE cn.id IN (5, 17)
  AND cc.id BETWEEN 75 AND 79
ON CONFLICT (creator_niche_id, content_class_id) DO NOTHING;

-- ── 8. Legacy → creator map ───────────────────────────────────────────
CREATE OR REPLACE FUNCTION map_legacy_niche_to_creator_niche(legacy_id INTEGER)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT CASE legacy_id
    WHEN 1  THEN 9
    WHEN 2  THEN 1
    WHEN 3  THEN 2
    WHEN 4  THEN 3
    WHEN 5  THEN 9
    WHEN 6  THEN 4
    WHEN 7  THEN 6
    WHEN 8  THEN 14
    WHEN 9  THEN 8
    WHEN 10 THEN 16
    WHEN 11 THEN 7
    WHEN 12 THEN 9
    WHEN 13 THEN 5   -- Hài → Comedy UX niche (restored v2)
    WHEN 14 THEN 12
    WHEN 15 THEN 9
    WHEN 16 THEN 11
    WHEN 17 THEN 8
    WHEN 18 THEN 3
    WHEN 19 THEN 4   -- Thú cưng (retired) → Lifestyle
    WHEN 20 THEN 4   -- Nhà cửa (retired) → Lifestyle
    WHEN 21 THEN 11
    WHEN 22 THEN 4
    WHEN 23 THEN 7
    WHEN 24 THEN 9
    WHEN 25 THEN 12
    WHEN 26 THEN 10
    WHEN 27 THEN 4   -- Đời sống · Tâm sự
    WHEN 29 THEN 17  -- Art & Craft ingest
    ELSE NULL
  END;
$$;

COMMIT;
