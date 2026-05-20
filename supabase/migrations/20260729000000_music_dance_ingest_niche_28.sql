-- Split Âm nhạc · Vũ đạo ingest from Đời sống · Tâm sự (option C).
-- UX creator_niche 15 → legacy niche_taxonomy 28; lifestyle stays on 27.
-- Rebases existing music content classes; Trends/Home filter by junction + niche_id.

BEGIN;

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  28,
  'Âm nhạc · Vũ đạo',
  'music_dance',
  ARRAY[
    '#nhac', '#nhactiktok', '#cover', '#coverhat', '#hatcover',
    '#dance', '#dancechallenge', '#dancetiktok', '#choreography',
    '#kpop', '#vpop', '#bolero', '#acoustic', '#livemusic',
    '#nhacche', '#nhacviet', '#tiktokdance', '#dancecover'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  signal_hashtags = EXCLUDED.signal_hashtags;

SELECT setval(
  'niche_taxonomy_id_seq',
  GREATEST(28, (SELECT COALESCE(MAX(id), 1) FROM niche_taxonomy))
);

-- Move indexed music rows off the lifestyle ingest bucket.
UPDATE video_corpus
SET niche_id = 28
WHERE niche_id = 27
  AND content_class_id IN (28, 29);

UPDATE video_corpus
SET inferred_creator_niche_id = 15
WHERE niche_id = 28
  AND (inferred_creator_niche_id IS NULL OR inferred_creator_niche_id IN (4, 5));

-- Music classes belong only under creator_niche 15 (not lifestyle browse).
DELETE FROM creator_niche_content_classes
WHERE creator_niche_id = 4
  AND content_class_id IN (28, 29);

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
    WHEN 13 THEN 4
    WHEN 14 THEN 12
    WHEN 15 THEN 9
    WHEN 16 THEN 11
    WHEN 17 THEN 8
    WHEN 18 THEN 3
    WHEN 19 THEN 4
    WHEN 20 THEN 4
    WHEN 21 THEN 11
    WHEN 22 THEN 15  -- K-pop (retired) → Music & Dance
    WHEN 23 THEN 7
    WHEN 24 THEN 9
    WHEN 25 THEN 12
    WHEN 26 THEN 10
    WHEN 27 THEN 4   -- Đời sống · Tâm sự
    WHEN 28 THEN 15  -- Âm nhạc · Vũ đạo
    ELSE NULL
  END;
$$;

COMMIT;
