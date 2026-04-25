-- Add niche 22: K-pop / Âm nhạc
--
-- Wave 5+ Phase 3 niche expansion. Splits music-focused content away
-- from the Chị đẹp aspirational-lifestyle bucket (niche 6) which was
-- absorbing Vpop + K-pop dance covers, MV reactions, artist content,
-- and music-montage reels. The Chị đẹp bucket has 76 'other'-format
-- rows (state-of-corpus Axis 2); a large share of those are music-
-- content that the aspirational-lifestyle framing doesn't serve.
--
-- Niche 21 was already taken in prod by "Thể thao & Ngoài trời"
-- (Sports & outdoor); this migration skips to id 22. The 2026-04-25
-- taxonomy expansion's highlight-format gate was
-- niche_id IN (6,16,17,21) — that stays valid for Sports (highlight-
-- natural) and is extended to include 22 (music) in a paired
-- corpus_ingest.py change in the same PR.
--
-- Hashtag strategy: Vietnamese-creator tags dominate (vpop / nhacviet),
-- with the top K-pop acts + local artists as niche-defining signals.
-- Format tags (#coversong / #dancecover) are included only when music-
-- specific — #cover alone is ambiguous so it's intentionally excluded.
--
-- Idempotent: INSERT ... ON CONFLICT DO NOTHING on both tables.

INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  22,
  'K-pop / Âm nhạc',
  'kpop_music',
  ARRAY[
    '#nhacviet', '#vpop', '#nhacvietnam', '#amnhacviet',
    '#nghenhacviet', '#nhactre', '#balladviet', '#songvn',
    '#kpop', '#kpopvietnam', '#kpopfan', '#kpopviet',
    '#blackpink', '#bts', '#newjeans', '#twice',
    '#straykids', '#aespa', '#lesserafim', '#ive',
    '#sontungmtp', '#soobin', '#hoangthuylinh', '#denvau',
    '#binz', '#erik', '#amee', '#hieuthuhai',
    '#coversong', '#covernhacviet', '#dancecover', '#dancecoverkpop',
    '#musicvideo', '#mvvietnam', '#nhacmoi', '#baihaymoingay',
    '#mashup', '#acoustic', '#livestage', '#singer'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Seed hashtag_niche_map for niche 22 — matches _resolve_niche_id() path.
-- All entries are niche-defining (niche_count = 1); if a tag later fires
-- on multiple niches the hashtag_map_confidence migration logic will
-- demote it automatically.
INSERT INTO hashtag_niche_map (hashtag, niche_id, occurrences, niche_count, source, is_generic)
VALUES
  ('nhacviet',          22, 100, 1, 'seed', false),
  ('vpop',              22, 100, 1, 'seed', false),
  ('nhacvietnam',       22, 100, 1, 'seed', false),
  ('amnhacviet',        22, 100, 1, 'seed', false),
  ('nghenhacviet',      22, 100, 1, 'seed', false),
  ('nhactre',           22, 100, 1, 'seed', false),
  ('balladviet',        22, 100, 1, 'seed', false),
  ('songvn',            22, 100, 1, 'seed', false),
  ('kpop',              22, 100, 1, 'seed', false),
  ('kpopvietnam',       22, 100, 1, 'seed', false),
  ('kpopfan',           22, 100, 1, 'seed', false),
  ('kpopviet',          22, 100, 1, 'seed', false),
  ('blackpink',         22, 100, 1, 'seed', false),
  ('bts',               22, 100, 1, 'seed', false),
  ('newjeans',          22, 100, 1, 'seed', false),
  ('twice',             22, 100, 1, 'seed', false),
  ('straykids',         22, 100, 1, 'seed', false),
  ('aespa',             22, 100, 1, 'seed', false),
  ('lesserafim',        22, 100, 1, 'seed', false),
  ('ive',               22, 100, 1, 'seed', false),
  ('sontungmtp',        22, 100, 1, 'seed', false),
  ('soobin',            22, 100, 1, 'seed', false),
  ('hoangthuylinh',     22, 100, 1, 'seed', false),
  ('denvau',            22, 100, 1, 'seed', false),
  ('binz',              22, 100, 1, 'seed', false),
  ('erik',              22, 100, 1, 'seed', false),
  ('amee',              22, 100, 1, 'seed', false),
  ('hieuthuhai',        22, 100, 1, 'seed', false),
  ('coversong',         22, 100, 1, 'seed', false),
  ('covernhacviet',     22, 100, 1, 'seed', false),
  ('dancecover',        22, 100, 1, 'seed', false),
  ('dancecoverkpop',    22, 100, 1, 'seed', false),
  ('musicvideo',        22, 100, 1, 'seed', false),
  ('mvvietnam',         22, 100, 1, 'seed', false),
  ('nhacmoi',           22, 100, 1, 'seed', false),
  ('baihaymoingay',     22, 100, 1, 'seed', false),
  ('mashup',            22, 100, 1, 'seed', false),
  ('acoustic',          22, 100, 1, 'seed', false),
  ('livestage',         22, 100, 1, 'seed', false),
  ('singer',            22, 100, 1, 'seed', false)
ON CONFLICT (hashtag) DO NOTHING;
