-- Fix niche 10 (Bất động sản / Real Estate) signal_hashtags.
-- Removes home decor / interior design tags that do not belong in real estate
-- (#noithat, #thietkenha, #homedesign, #noithathienroi) — reserved for a
-- future home decor niche. Keeps only genuine real estate signals.
-- Idempotent: re-running is safe.

UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#batdongsan', '#nhadat', '#muanha', '#thuenha',
  '#bantanha', '#canho', '#chungcu', '#vinhomes',
  '#masteri', '#batdongsanhanoi', '#batdongsansaigon',
  '#dautubds', '#nhapho', '#datchoviet', '#khodoithi',
  '#lienke', '#thuenhahanoi', '#chothue', '#kinhsbds',
  '#reviewcanho', '#muabannhadat', '#batdongsanviet',
  '#investproperty', '#realestatevietnam'
] WHERE id = 10;

-- Re-seed hashtag_niche_map for the updated tag list.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('batdongsan',         10, 100, 1, 'seed', false),
  ('nhadat',             10, 100, 1, 'seed', false),
  ('muanha',             10, 100, 1, 'seed', false),
  ('thuenha',            10, 100, 1, 'seed', false),
  ('bantanha',           10, 100, 1, 'seed', false),
  ('canho',              10, 100, 1, 'seed', false),
  ('chungcu',            10, 100, 1, 'seed', false),
  ('vinhomes',           10, 100, 1, 'seed', false),
  ('masteri',            10, 100, 1, 'seed', false),
  ('batdongsanhanoi',    10, 100, 1, 'seed', false),
  ('batdongsansaigon',   10, 100, 1, 'seed', false),
  ('dautubds',           10, 100, 1, 'seed', false),
  ('nhapho',             10, 100, 1, 'seed', false),
  ('datchoviet',         10, 100, 1, 'seed', false),
  ('khodoithi',          10, 100, 1, 'seed', false),
  ('lienke',             10, 100, 1, 'seed', false),
  ('thuenhahanoi',       10, 100, 1, 'seed', false),
  ('chothue',            10, 100, 1, 'seed', false),
  ('kinhsbds',           10, 100, 1, 'seed', false),
  ('reviewcanho',        10, 100, 1, 'seed', false),
  ('muabannhadat',       10, 100, 1, 'seed', false),
  ('batdongsanviet',     10, 100, 1, 'seed', false),
  ('investproperty',     10, 100, 1, 'seed', false),
  ('realestatevietnam',  10, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
