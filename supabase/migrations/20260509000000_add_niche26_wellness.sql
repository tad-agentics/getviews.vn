-- Add niche 26: Sức khoẻ / Wellness.
--
-- Wellness was a documented gap — Vietnamese creators making
-- mental health, mindfulness, sleep hygiene, nutrition for recovery
-- (not weight-loss), supplements, morning/night routines, yoga/
-- meditation content had no home. Their content drifted into
-- niche 8 (Gym) where it didn't fit (gym hooks are face-to-camera
-- form tutorials, not vlog routines), niche 7 (Mẹ bỉm), or niche 13
-- (Hài / Giải trí) by default.
--
-- Per request: signal_hashtags include both English-loanword
-- wellness tags AND Vietnamese-broad health tags (#sukhoe,
-- #songkhoe, etc.), so creators using either vocabulary route
-- correctly via _resolve_niche_id().
--
-- Niche IDs 23-25 were retired but their numeric ids are taken;
-- niche 26 is the next free slot. SERIAL sequence is bumped at
-- the end so future fresh-clone INSERTs get id ≥ 27.
--
-- Boundary calls (cross-niche tag policy):
--   - #yoga / #yogavietnam land HERE not niche 8 (yoga consumed as
--     mindfulness/recovery not as gym training). #tapgym, #fitness,
--     #giamcan stay with niche 8.
--   - #anlanh, #healthyeating land HERE not niche 4 (health-driven
--     eating, not "ăn gì đâu ngon"). #monchay, #nauanchay stay with
--     niche 4.
--   - #morningroutine — historically leaked to retired niche 6;
--     primary home now is wellness.
--   - #stress, #anxiety, #suckhoetinhthan all land here.
--
-- Idempotent: INSERT ... ON CONFLICT DO NOTHING.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  26,
  'Sức khoẻ / Wellness',
  'wellness',
  ARRAY[
    -- Wellness (English loanwords, common on VN TikTok)
    '#wellness', '#wellnessvietnam', '#selfcare', '#mindfulness',
    '#morningroutine', '#nightroutine', '#routinhanngay', '#habitstacking',
    -- Sức khoẻ general (Vietnamese broad)
    '#sukhoe', '#songkhoe', '#songkhoemanh', '#suckhoenu', '#suckhoenam',
    '#suckhoetotcho', '#cleanliving', '#songxanh',
    -- Mental health / mindfulness
    '#tinhtam', '#tinhthancantam', '#suckhoetinhthan', '#yenbinh',
    '#anlinh', '#stress', '#stressmanagement', '#anxiety',
    -- Sleep
    '#ngutot', '#ngusau', '#giacngu', '#thoiquentot', '#insomnia',
    -- Yoga / meditation
    '#yoga', '#yogavietnam', '#yogaeveryday', '#meditation',
    '#thiendinh', '#thien', '#thienending',
    -- Healthy eating (wellness-framed, NOT weight-loss)
    '#anlanh', '#anuonglanhmanh', '#thucphamlanhmanh', '#healthyfood',
    '#healthyeating', '#anuongcanbang', '#greensmoothie', '#nuocep',
    -- Supplements / vitamins
    '#thucphamchucnang', '#supplement', '#vitamin',
    '#collagen', '#omega3', '#probiotics', '#magie',
    -- Recovery / body care (non-training)
    '#recovery', '#stretching', '#phuchoiconbody',
    -- Detox / cleansing
    '#detox', '#thanhloccodien', '#cleanse', '#thanhdoc',
    -- Holistic lifestyle
    '#lifestylevietnam', '#womenhealthvietnam', '#sanluocsong'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 26's defining tags. Generic /
-- cross-niche tags (#stress, #yoga ambiguous) are seeded with
-- niche_count=1 for now; the hashtag_map_confidence cron will demote
-- them if they fire across >1 niche after corpus grows.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
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

-- Bump SERIAL so a fresh-clone INSERT after this migration starts at id ≥ 27
-- (matches the pattern at the end of 20260409000001_niche_taxonomy.sql).
SELECT setval('niche_taxonomy_id_seq', GREATEST(26, (SELECT COALESCE(MAX(id), 1) FROM niche_taxonomy)));
