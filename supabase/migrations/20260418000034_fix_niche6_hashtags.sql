-- Fix niche 6 (Chị đẹp / Lifestyle identity) signal_hashtags.
-- Removes cross-niche tags that co-occur with làm đẹp (2), thời trang (3),
-- and parenting (7) content, causing classify_from_hashtags ambiguity.
-- Keeps only signals that specifically index "chị đẹp" creator identity.
-- Idempotent: re-running is safe.

UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#chidep', '#hotgirl', '#hotgirlviet', '#covai', '#songdep', '#dailylife',
  '#girlboss', '#phunut', '#congviec', '#thanhcong', '#dayinmylife',
  '#livingalone', '#tuvuytinh', '#girly', '#congchua', '#lifestylevietnam',
  '#livingmybestlife', '#phongcachsong', '#hotgirllifestyle', '#chilamdep'
] WHERE id = 6;

-- Re-seed hashtag_niche_map for the updated tag list.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('chidep',             6, 100, 1, 'seed', false),
  ('hotgirl',            6, 100, 1, 'seed', false),
  ('hotgirlviet',        6, 100, 1, 'seed', false),
  ('covai',              6, 100, 1, 'seed', false),
  ('songdep',            6, 100, 1, 'seed', false),
  ('dailylife',          6, 100, 1, 'seed', false),
  ('girlboss',           6, 100, 1, 'seed', false),
  ('phunut',             6, 100, 1, 'seed', false),
  ('congviec',           6, 100, 1, 'seed', false),
  ('thanhcong',          6, 100, 1, 'seed', false),
  ('dayinmylife',        6, 100, 1, 'seed', false),
  ('livingalone',        6, 100, 1, 'seed', false),
  ('tuvuytinh',          6, 100, 1, 'seed', false),
  ('girly',              6, 100, 1, 'seed', false),
  ('congchua',           6, 100, 1, 'seed', false),
  ('lifestylevietnam',   6, 100, 1, 'seed', false),
  ('livingmybestlife',   6, 100, 1, 'seed', false),
  ('phongcachsong',      6, 100, 1, 'seed', false),
  ('hotgirllifestyle',   6, 100, 1, 'seed', false),
  ('chilamdep',          6, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
