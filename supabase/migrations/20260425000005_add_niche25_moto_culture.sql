-- Add niche 25: Xe máy / Moto culture
--
-- Wave 5+ Phase 3 niche expansion. Splits motovlog / touring / group-
-- ride / custom-build / racing-culture content away from Ô tô / Xe máy
-- (niche 14), which is heavily tilted toward review/buying-guide
-- content. Moto-culture creators have format conventions (helmet-cam
-- POV touring, group-ride compilations, build-progress montages,
-- track-day highlights) that the review-focused niche doesn't surface
-- well.
--
-- Hashtag strategy: lifestyle / community / racing / build-culture
-- tags are niche-defining; review-style tags (#reviewxemay,
-- #reviewxedien, #vinfast) intentionally stay with niche 14. Some
-- shared tags (#motovlog, #xuyenviet) are kept in this niche's
-- signal_hashtags array but ON CONFLICT DO NOTHING preserves their
-- existing niche-14 mapping in hashtag_niche_map.
--
-- classify_format: highlight-bucket gate extended to include niche_id
-- 25 in a paired corpus_ingest.py change in the same PR — touring /
-- group-ride compilations are canonical highlight-format content.
--
-- Idempotent: ON CONFLICT DO NOTHING on both tables.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  25,
  'Xe máy / Moto culture',
  'moto_culture',
  ARRAY[
    -- Touring / lifestyle (niche-defining)
    '#motovlogvietnam', '#motorlife', '#bikerlife',
    '#motorcyclelife', '#twowheels', '#twowheellife',
    '#ridevietnam', '#phuottren2banh', '#phuotxemay',
    '#duongmonhochiminh', '#truongsonduong', '#qua_deo',
    '#detehadi', '#dieukhienxenhanh',
    -- Group rides / community
    '#anhem2banh', '#dauthecodo', '#groupride',
    '#tourxemay', '#hoixemoto', '#hoiyeuxe',
    '#camerahanhtrinh', '#actioncam', '#gopromoto',
    -- Build / custom culture
    '#dolexemay', '#donoixe', '#custommoto',
    '#caferacervietnam', '#bobbervietnam', '#scramblervietnam',
    '#hondamonkey', '#hondavietnam', '#motonhapkhau',
    '#pkl', '#xemoto', '#bigbike',
    '#bigbikevietnam', '#kawasaki', '#ducati',
    '#bmwmotorrad', '#harleydavidson', '#triumph',
    -- Track / racing
    '#trackday', '#trackdayvietnam', '#duaxe',
    '#duaxehanoi', '#sport_riding', '#wheelie',
    '#wheelievietnam', '#stuntridingvietnam',
    -- Specific bike models / culture markers
    '#exciter150', '#exciter155', '#raider150',
    '#satria', '#winner_x', '#cb150',
    '#z1000', '#mt07', '#mt09',
    '#r3vietnam', '#r6', '#cbr150r',
    '#tracer', '#nmax', '#xmax',
    '#vario', '#airblade150', '#sh125'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 25. ON CONFLICT DO NOTHING preserves
-- existing niche-14 mappings for shared tags like #motovlog.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('motovlogvietnam',     25, 100, 1, 'seed', false),
  ('motorlife',           25, 100, 1, 'seed', false),
  ('bikerlife',           25, 100, 1, 'seed', false),
  ('motorcyclelife',      25, 100, 1, 'seed', false),
  ('twowheels',           25, 100, 1, 'seed', false),
  ('twowheellife',        25, 100, 1, 'seed', false),
  ('ridevietnam',         25, 100, 1, 'seed', false),
  ('phuottren2banh',      25, 100, 1, 'seed', false),
  ('phuotxemay',          25, 100, 1, 'seed', false),
  ('duongmonhochiminh',   25, 100, 1, 'seed', false),
  ('qua_deo',             25, 100, 1, 'seed', false),
  ('anhem2banh',          25, 100, 1, 'seed', false),
  ('groupride',           25, 100, 1, 'seed', false),
  ('tourxemay',           25, 100, 1, 'seed', false),
  ('hoixemoto',           25, 100, 1, 'seed', false),
  ('hoiyeuxe',            25, 100, 1, 'seed', false),
  ('camerahanhtrinh',     25, 100, 1, 'seed', false),
  ('actioncam',           25, 100, 1, 'seed', false),
  ('gopromoto',           25, 100, 1, 'seed', false),
  ('dolexemay',           25, 100, 1, 'seed', false),
  ('donoixe',             25, 100, 1, 'seed', false),
  ('custommoto',          25, 100, 1, 'seed', false),
  ('caferacervietnam',    25, 100, 1, 'seed', false),
  ('bobbervietnam',       25, 100, 1, 'seed', false),
  ('scramblervietnam',    25, 100, 1, 'seed', false),
  ('hondamonkey',         25, 100, 1, 'seed', false),
  ('hondavietnam',        25, 100, 1, 'seed', false),
  ('motonhapkhau',        25, 100, 1, 'seed', false),
  ('pkl',                 25, 100, 1, 'seed', false),
  ('xemoto',              25, 100, 1, 'seed', false),
  ('bigbike',             25, 100, 1, 'seed', false),
  ('bigbikevietnam',      25, 100, 1, 'seed', false),
  ('kawasaki',            25, 100, 1, 'seed', false),
  ('ducati',              25, 100, 1, 'seed', false),
  ('bmwmotorrad',         25, 100, 1, 'seed', false),
  ('harleydavidson',      25, 100, 1, 'seed', false),
  ('triumph',             25, 100, 1, 'seed', false),
  ('trackday',            25, 100, 1, 'seed', false),
  ('trackdayvietnam',     25, 100, 1, 'seed', false),
  ('duaxe',               25, 100, 1, 'seed', false),
  ('duaxehanoi',          25, 100, 1, 'seed', false),
  ('sport_riding',        25, 100, 1, 'seed', false),
  ('wheelie',             25, 100, 1, 'seed', false),
  ('wheelievietnam',      25, 100, 1, 'seed', false),
  ('stuntridingvietnam',  25, 100, 1, 'seed', false),
  ('exciter150',          25, 100, 1, 'seed', false),
  ('exciter155',          25, 100, 1, 'seed', false),
  ('raider150',           25, 100, 1, 'seed', false),
  ('satria',              25, 100, 1, 'seed', false),
  ('winner_x',            25, 100, 1, 'seed', false),
  ('cb150',               25, 100, 1, 'seed', false),
  ('z1000',               25, 100, 1, 'seed', false),
  ('mt07',                25, 100, 1, 'seed', false),
  ('mt09',                25, 100, 1, 'seed', false),
  ('r3vietnam',           25, 100, 1, 'seed', false),
  ('r6',                  25, 100, 1, 'seed', false),
  ('cbr150r',             25, 100, 1, 'seed', false),
  ('tracer',              25, 100, 1, 'seed', false),
  ('nmax',                25, 100, 1, 'seed', false),
  ('xmax',                25, 100, 1, 'seed', false),
  ('vario',               25, 100, 1, 'seed', false),
  ('airblade150',         25, 100, 1, 'seed', false),
  ('sh125',               25, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
