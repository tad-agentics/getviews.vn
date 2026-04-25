-- Add niche 21: Thể thao & Ngoài trời (Sports & outdoor)
--
-- Retroactive sync migration. Niche 21 was added to prod
-- (niche_taxonomy + 103 video_corpus rows ingesting as of 2026-04-25)
-- via an out-of-band operation not tracked in git. This migration
-- reconciles that drift so a fresh clone of the database gets niche
-- 21 correctly. It is intentionally dated 2026-04-24 to place it
-- before the 2026-04-25 niche 22 (K-pop / Âm nhạc) migration even
-- though the two are committed together — this preserves the
-- logical prod order.
--
-- Per CLAUDE.md: "migrations in supabase/migrations/ — both Supabase
-- MCP (remote apply) and local SQL file must be written; they must
-- never drift." — Sports niche was a drift violation; this is the
-- remediation.
--
-- The niche 21 slot is used by the Wave 5+ taxonomy expansion's
-- highlight-format gate (classify_format: niche_id IN (6,16,17,21)).
-- Sports montage clips are a canonical highlight-format fit.
--
-- Idempotent: ON CONFLICT DO NOTHING; if the row + seeds already
-- exist (which they do in prod as of commit time) this is a no-op.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  21,
  'Thể thao & Ngoài trời',
  'Sports & outdoor activities',
  ARRAY[
    '#thethao', '#bongda', '#chaybo', '#cycling',
    '#leonui', '#ngoaitroi', '#footballvietnam', '#vleague',
    '#bongdavietnam', '#caulongvietnam', '#badminton', '#bongro',
    '#tennis', '#pickleball', '#pickleballvietnam', '#marathon',
    '#chaybovietnam', '#runvietnam', '#5km', '#10km',
    '#running', '#xedap', '#xedapdiahinh', '#xedapduongdai',
    '#mtb', '#camping', '#campingvietnam', '#trekking',
    '#trekkingvietnam', '#hiking', '#hikingvietnam', '#outdoorvietnam',
    '#phongtrao', '#surfing', '#kayaking', '#swimmingvietnam',
    '#muaythai', '#boxing', '#bjj', '#vovinam',
    '#vocodotruyen', '#reviewdothethao', '#gearoutdoor',
    '#reviewgiayrunning', '#sportstips', '#gym', '#gymlife',
    '#calisthenics', '#swim', '#swimming', '#boi',
    '#freediving', '#tapluyenmoingay', '#giammo',
    '#giamcankhoahoc', '#giamcanlanhmanh', '#songkhoe',
    '#theducthethao', '#dabong', '#cauthubongda', '#thethao247',
    '#wwe', '#dienkinh', '#gokart', '#kyluat',
    '#strong', '#ngua'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 21 — the prod row was added
-- without seeding the map, so _resolve_niche_id() currently has no
-- fast-path for Sports hashtags. This seed closes that gap.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('thethao',              21, 100, 1, 'seed', false),
  ('bongda',               21, 100, 1, 'seed', false),
  ('chaybo',               21, 100, 1, 'seed', false),
  ('cycling',              21, 100, 1, 'seed', false),
  ('leonui',               21, 100, 1, 'seed', false),
  ('ngoaitroi',            21, 100, 1, 'seed', false),
  ('footballvietnam',      21, 100, 1, 'seed', false),
  ('vleague',              21, 100, 1, 'seed', false),
  ('bongdavietnam',        21, 100, 1, 'seed', false),
  ('caulongvietnam',       21, 100, 1, 'seed', false),
  ('badminton',            21, 100, 1, 'seed', false),
  ('bongro',               21, 100, 1, 'seed', false),
  ('tennis',               21, 100, 1, 'seed', false),
  ('pickleball',           21, 100, 1, 'seed', false),
  ('pickleballvietnam',    21, 100, 1, 'seed', false),
  ('marathon',             21, 100, 1, 'seed', false),
  ('chaybovietnam',        21, 100, 1, 'seed', false),
  ('runvietnam',           21, 100, 1, 'seed', false),
  ('5km',                  21, 100, 1, 'seed', false),
  ('10km',                 21, 100, 1, 'seed', false),
  ('running',              21, 100, 1, 'seed', false),
  ('xedap',                21, 100, 1, 'seed', false),
  ('xedapdiahinh',         21, 100, 1, 'seed', false),
  ('xedapduongdai',        21, 100, 1, 'seed', false),
  ('mtb',                  21, 100, 1, 'seed', false),
  ('camping',              21, 100, 1, 'seed', false),
  ('campingvietnam',       21, 100, 1, 'seed', false),
  ('trekking',             21, 100, 1, 'seed', false),
  ('trekkingvietnam',      21, 100, 1, 'seed', false),
  ('hiking',               21, 100, 1, 'seed', false),
  ('hikingvietnam',        21, 100, 1, 'seed', false),
  ('outdoorvietnam',       21, 100, 1, 'seed', false),
  ('surfing',              21, 100, 1, 'seed', false),
  ('kayaking',             21, 100, 1, 'seed', false),
  ('swimmingvietnam',      21, 100, 1, 'seed', false),
  ('muaythai',             21, 100, 1, 'seed', false),
  ('boxing',               21, 100, 1, 'seed', false),
  ('bjj',                  21, 100, 1, 'seed', false),
  ('vovinam',              21, 100, 1, 'seed', false),
  ('vocodotruyen',         21, 100, 1, 'seed', false),
  ('reviewdothethao',      21, 100, 1, 'seed', false),
  ('gearoutdoor',          21, 100, 1, 'seed', false),
  ('reviewgiayrunning',    21, 100, 1, 'seed', false),
  ('sportstips',           21, 100, 1, 'seed', false),
  ('calisthenics',         21, 100, 1, 'seed', false),
  ('freediving',           21, 100, 1, 'seed', false),
  ('tapluyenmoingay',      21, 100, 1, 'seed', false),
  ('theducthethao',        21, 100, 1, 'seed', false),
  ('dabong',               21, 100, 1, 'seed', false),
  ('cauthubongda',         21, 100, 1, 'seed', false),
  ('thethao247',           21, 100, 1, 'seed', false),
  ('wwe',                  21, 100, 1, 'seed', false),
  ('dienkinh',             21, 100, 1, 'seed', false),
  ('gokart',               21, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
