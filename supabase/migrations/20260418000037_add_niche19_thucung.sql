-- Add niche 19: Thú cưng / Pets
-- Idempotent: INSERT ... ON CONFLICT DO NOTHING.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  19,
  'Thú cưng',
  'pets',
  ARRAY[
    '#thucung', '#meovacho', '#meoviet', '#choviet',
    '#petcare', '#petlover', '#meo', '#cho', '#thucungvietnam',
    '#petfood', '#dogvietnam', '#catvietnam', '#meodep',
    '#chodep', '#nuoichomeo', '#thucungdangiu', '#pets',
    '#petlife', '#petowner', '#catlovers', '#doglovers',
    '#groomingpet', '#vetsinh', '#thuyviet', '#ca'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 19.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('thucung',         19, 100, 1, 'seed', false),
  ('meovacho',        19, 100, 1, 'seed', false),
  ('meoviet',         19, 100, 1, 'seed', false),
  ('choviet',         19, 100, 1, 'seed', false),
  ('petcare',         19, 100, 1, 'seed', false),
  ('petlover',        19, 100, 1, 'seed', false),
  ('meo',             19, 100, 1, 'seed', false),
  ('cho',             19, 100, 1, 'seed', false),
  ('thucungvietnam',  19, 100, 1, 'seed', false),
  ('petfood',         19, 100, 1, 'seed', false),
  ('dogvietnam',      19, 100, 1, 'seed', false),
  ('catvietnam',      19, 100, 1, 'seed', false),
  ('meodep',          19, 100, 1, 'seed', false),
  ('chodep',          19, 100, 1, 'seed', false),
  ('nuoichomeo',      19, 100, 1, 'seed', false),
  ('thucungdangiu',   19, 100, 1, 'seed', false),
  ('pets',            19, 100, 1, 'seed', false),
  ('petlife',         19, 100, 1, 'seed', false),
  ('petowner',        19, 100, 1, 'seed', false),
  ('catlovers',       19, 100, 1, 'seed', false),
  ('doglovers',       19, 100, 1, 'seed', false),
  ('groomingpet',     19, 100, 1, 'seed', false),
  ('vetsinh',         19, 100, 1, 'seed', false),
  ('thuyviet',        19, 100, 1, 'seed', false),
  ('ca',              19, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
