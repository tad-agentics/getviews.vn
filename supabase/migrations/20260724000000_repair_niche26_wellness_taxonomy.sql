-- Repair: niche_taxonomy id=26 (Wellness) missing on production despite
-- schema_migrations version 20260509000000 being recorded.
--
-- Symptom (2026-05-19 batch ingest): HI-11 route maps creator_niches.id=10
-- (wellness) → legacy niche_id=26 via profile_niches / corpus_ingest;
-- upsert fails with video_corpus_niche_id_fkey (110 analyzed rows lost).
--
-- Prod check: SELECT * FROM niche_taxonomy WHERE id >= 19 → only 19–21;
-- id=26 returns zero rows while 20260509000000 is in schema_migrations.
--
-- Idempotent: safe on fresh clones that already have row 26.

BEGIN;

INSERT INTO public.niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  26,
  'Sức khoẻ / Wellness',
  'wellness',
  ARRAY[
    '#wellness', '#wellnessvietnam', '#selfcare', '#mindfulness',
    '#morningroutine', '#nightroutine', '#routinhanngay', '#habitstacking',
    '#sukhoe', '#songkhoe', '#songkhoemanh', '#suckhoenu', '#suckhoenam',
    '#suckhoetotcho', '#cleanliving', '#songxanh',
    '#tinhtam', '#tinhthancantam', '#suckhoetinhthan', '#yenbinh',
    '#anlinh', '#stress', '#stressmanagement', '#anxiety',
    '#ngutot', '#ngusau', '#giacngu', '#thoiquentot', '#insomnia',
    '#yoga', '#yogavietnam', '#yogaeveryday', '#meditation',
    '#thiendinh', '#thien', '#thienending',
    '#anlanh', '#anuonglanhmanh', '#thucphamlanhmanh', '#healthyfood',
    '#healthyeating', '#anuongcanbang', '#greensmoothie', '#nuocep',
    '#thucphamchucnang', '#supplement', '#vitamin',
    '#collagen', '#omega3', '#probiotics', '#magie',
    '#recovery', '#stretching', '#phuchoiconbody',
    '#detox', '#thanhloccodien', '#cleanse', '#thanhdoc',
    '#lifestylevietnam', '#womenhealthvietnam', '#sanluocsong'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  signal_hashtags = EXCLUDED.signal_hashtags;

INSERT INTO public.hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('wellness',          26, 100, 1, 'seed', false),
  ('wellnessvietnam',   26, 100, 1, 'seed', false),
  ('selfcare',          26, 100, 1, 'seed', false),
  ('mindfulness',       26, 100, 1, 'seed', false),
  ('morningroutine',    26, 100, 1, 'seed', false),
  ('nightroutine',      26, 100, 1, 'seed', false),
  ('routinhanngay',     26, 100, 1, 'seed', false),
  ('habitstacking',     26, 100, 1, 'seed', false),
  ('sukhoe',            26, 100, 1, 'seed', false),
  ('songkhoe',          26, 100, 1, 'seed', false),
  ('songkhoemanh',      26, 100, 1, 'seed', false),
  ('suckhoenu',         26, 100, 1, 'seed', false),
  ('suckhoenam',        26, 100, 1, 'seed', false),
  ('cleanliving',       26, 100, 1, 'seed', false),
  ('songxanh',          26, 100, 1, 'seed', false),
  ('tinhtam',           26, 100, 1, 'seed', false),
  ('tinhthancantam',    26, 100, 1, 'seed', false),
  ('suckhoetinhthan',   26, 100, 1, 'seed', false),
  ('yenbinh',           26, 100, 1, 'seed', false),
  ('stressmanagement',  26, 100, 1, 'seed', false),
  ('ngutot',            26, 100, 1, 'seed', false),
  ('ngusau',            26, 100, 1, 'seed', false),
  ('giacngu',           26, 100, 1, 'seed', false),
  ('thoiquentot',       26, 100, 1, 'seed', false),
  ('insomnia',          26, 100, 1, 'seed', false),
  ('yoga',              26, 100, 1, 'seed', false),
  ('yogavietnam',       26, 100, 1, 'seed', false),
  ('yogaeveryday',      26, 100, 1, 'seed', false),
  ('meditation',        26, 100, 1, 'seed', false),
  ('thiendinh',         26, 100, 1, 'seed', false),
  ('thienending',       26, 100, 1, 'seed', false),
  ('anlanh',            26, 100, 1, 'seed', false),
  ('anuonglanhmanh',    26, 100, 1, 'seed', false),
  ('thucphamlanhmanh',  26, 100, 1, 'seed', false),
  ('healthyeating',     26, 100, 1, 'seed', false),
  ('anuongcanbang',     26, 100, 1, 'seed', false),
  ('greensmoothie',     26, 100, 1, 'seed', false),
  ('nuocep',            26, 100, 1, 'seed', false),
  ('thucphamchucnang',  26, 100, 1, 'seed', false),
  ('supplement',        26, 100, 1, 'seed', false),
  ('collagen',          26, 100, 1, 'seed', false),
  ('omega3',            26, 100, 1, 'seed', false),
  ('probiotics',        26, 100, 1, 'seed', false),
  ('magie',             26, 100, 1, 'seed', false),
  ('phuchoiconbody',    26, 100, 1, 'seed', false),
  ('thanhloccodien',    26, 100, 1, 'seed', false),
  ('cleanse',           26, 100, 1, 'seed', false),
  ('thanhdoc',          26, 100, 1, 'seed', false),
  ('womenhealthvietnam', 26, 100, 1, 'seed', false),
  ('sanluocsong',       26, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;

SELECT setval(
  'niche_taxonomy_id_seq',
  GREATEST(26, (SELECT COALESCE(MAX(id), 1) FROM public.niche_taxonomy))
);

COMMIT;
