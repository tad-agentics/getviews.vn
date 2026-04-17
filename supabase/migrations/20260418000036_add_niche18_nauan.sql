-- Add niche 18: Nấu ăn / Home Cooking
-- Idempotent: INSERT ... ON CONFLICT DO NOTHING and IF NOT EXISTS guards.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  18,
  'Nấu ăn / Công thức',
  'home_cooking',
  ARRAY[
    '#nauan', '#nauanngon', '#congthucnauan', '#nauanmoiday',
    '#buacomgiadinh', '#monngonmoingay', '#daubepper', '#nauanhanoi',
    '#nauansaigon', '#recipevietnam', '#cookingtutorial',
    '#nauanfacebook', '#congthucmoingay', '#amthucviet',
    '#nauancungcon', '#monchay', '#nauanchay', '#anlanh',
    '#chefvietnam', '#homecooking', '#mealprep', '#benhnaunan',
    '#nauankhoe', '#combinh', '#nauantaigia'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 18.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('nauan',              18, 100, 1, 'seed', false),
  ('nauanngon',          18, 100, 1, 'seed', false),
  ('congthucnauan',      18, 100, 1, 'seed', false),
  ('nauanmoiday',        18, 100, 1, 'seed', false),
  ('buacomgiadinh',      18, 100, 1, 'seed', false),
  ('monngonmoingay',     18, 100, 1, 'seed', false),
  ('daubepper',          18, 100, 1, 'seed', false),
  ('nauanhanoi',         18, 100, 1, 'seed', false),
  ('nauansaigon',        18, 100, 1, 'seed', false),
  ('recipevietnam',      18, 100, 1, 'seed', false),
  ('cookingtutorial',    18, 100, 1, 'seed', false),
  ('nauanfacebook',      18, 100, 1, 'seed', false),
  ('congthucmoingay',    18, 100, 1, 'seed', false),
  ('amthucviet',         18, 100, 1, 'seed', false),
  ('nauancungcon',       18, 100, 1, 'seed', false),
  ('monchay',            18, 100, 1, 'seed', false),
  ('nauanchay',          18, 100, 1, 'seed', false),
  ('anlanh',             18, 100, 1, 'seed', false),
  ('chefvietnam',        18, 100, 1, 'seed', false),
  ('homecooking',        18, 100, 1, 'seed', false),
  ('mealprep',           18, 100, 1, 'seed', false),
  ('benhnaunan',         18, 100, 1, 'seed', false),
  ('nauankhoe',          18, 100, 1, 'seed', false),
  ('combinh',            18, 100, 1, 'seed', false),
  ('nauantaigia',        18, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
