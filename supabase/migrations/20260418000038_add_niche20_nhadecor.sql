-- Add niche 20: Nhà cửa / Nội thất (Home Decor)
-- Receives the home decor tags removed from niche 10 (BĐS) in migration 35.
-- Idempotent: INSERT ... ON CONFLICT DO NOTHING.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  20,
  'Nhà cửa / Nội thất',
  'home_decor',
  ARRAY[
    '#noithat', '#thietkenha', '#trangtrinhacua', '#homedecor',
    '#homedesignvietnam', '#phongkhacdep', '#organization',
    '#roomtour', '#nhatoi', '#canhotour', '#dichnuvnha',
    '#decorvietnam', '#homestyling', '#interiordesign',
    '#thietkenoithat', '#noidecor', '#nhatrangdep',
    '#nhabep', '#phongngudep', '#tidyup', '#organise',
    '#homedesign', '#smallapartment', '#canhoviet',
    '#livingroomdecor', '#diyhome'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 20.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('noithat',            20, 100, 1, 'seed', false),
  ('thietkenha',         20, 100, 1, 'seed', false),
  ('trangtrinhacua',     20, 100, 1, 'seed', false),
  ('homedecor',          20, 100, 1, 'seed', false),
  ('homedesignvietnam',  20, 100, 1, 'seed', false),
  ('phongkhacdep',       20, 100, 1, 'seed', false),
  ('organization',       20, 100, 1, 'seed', false),
  ('roomtour',           20, 100, 1, 'seed', false),
  ('nhatoi',             20, 100, 1, 'seed', false),
  ('canhotour',          20, 100, 1, 'seed', false),
  ('dichnuvnha',         20, 100, 1, 'seed', false),
  ('decorvietnam',       20, 100, 1, 'seed', false),
  ('homestyling',        20, 100, 1, 'seed', false),
  ('interiordesign',     20, 100, 1, 'seed', false),
  ('thietkenoithat',     20, 100, 1, 'seed', false),
  ('noidecor',           20, 100, 1, 'seed', false),
  ('nhatrangdep',        20, 100, 1, 'seed', false),
  ('nhabep',             20, 100, 1, 'seed', false),
  ('phongngudep',        20, 100, 1, 'seed', false),
  ('tidyup',             20, 100, 1, 'seed', false),
  ('organise',           20, 100, 1, 'seed', false),
  ('homedesign',         20, 100, 1, 'seed', false),
  ('smallapartment',     20, 100, 1, 'seed', false),
  ('canhoviet',          20, 100, 1, 'seed', false),
  ('livingroomdecor',    20, 100, 1, 'seed', false),
  ('diyhome',            20, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
