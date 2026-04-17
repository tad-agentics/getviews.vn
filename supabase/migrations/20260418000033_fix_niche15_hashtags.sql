-- Fix niche 15 (Tài chính / Personal Finance) signal_hashtags.
-- Removes crypto/forex/scam-adjacent tags; replaces with genuine Vietnamese
-- personal finance signals (tiết kiệm, quản lý chi tiêu, tài chính cá nhân).
-- Idempotent: re-running is safe.

UPDATE niche_taxonomy SET signal_hashtags = ARRAY[
  '#taichinh', '#taichinhcanhan', '#tietkiem', '#dautu',
  '#quanlychitieu', '#tietkiemthongminh', '#chungkhoan',
  '#cophieu', '#quydautu', '#nghihuu', '#FIRE',
  '#financialfreedom', '#richhabits', '#hoachdinhcuocsong',
  '#taichinhvietnam', '#kiemtienthongminh', '#canhbaodautu',
  '#thitruong', '#laisuatnganhang', '#vangbac'
] WHERE id = 15;

-- Re-seed hashtag_niche_map for the new tags.
-- Old removed tags will remain in hashtag_niche_map with their existing
-- occurrences but lose the niche_taxonomy backing — they decay naturally.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('taichinh',            15, 100, 1, 'seed', false),
  ('taichinhcanhan',      15, 100, 1, 'seed', false),
  ('tietkiem',            15, 100, 1, 'seed', false),
  ('dautu',               15, 100, 1, 'seed', false),
  ('quanlychitieu',       15, 100, 1, 'seed', false),
  ('tietkiemthongminh',   15, 100, 1, 'seed', false),
  ('chungkhoan',          15, 100, 1, 'seed', false),
  ('cophieu',             15, 100, 1, 'seed', false),
  ('quydautu',            15, 100, 1, 'seed', false),
  ('nghihuu',             15, 100, 1, 'seed', false),
  ('fire',                15, 100, 1, 'seed', false),
  ('financialfreedom',    15, 100, 1, 'seed', false),
  ('richhabits',          15, 100, 1, 'seed', false),
  ('hoachdinhcuocsong',   15, 100, 1, 'seed', false),
  ('taichinhvietnam',     15, 100, 1, 'seed', false),
  ('kiemtienthongminh',   15, 100, 1, 'seed', false),
  ('canhbaodautu',        15, 100, 1, 'seed', false),
  ('thitruong',           15, 100, 1, 'seed', false),
  ('laisuatnganhang',     15, 100, 1, 'seed', false),
  ('vangbac',             15, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
