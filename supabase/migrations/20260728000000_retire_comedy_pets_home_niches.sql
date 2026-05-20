-- Retire UX creator niches ``comedy`` (5) and ``pets_home`` (13); merge legacy
-- ingest buckets Hài (13), Thú cưng (19), Nhà cửa (20) into new
-- ``Đời sống · Tâm sự`` (27). Overlap between lifestyle (4) and comedy (5)
-- confused onboarding — one lifestyle bucket for vlog, tâm sự, hài relatable,
-- thú cưng, decor.
--
-- Strategy (mirrors niche-6 / niche-22 retirements, but corpus is REBADGED not
-- deleted):
--   1. INSERT legacy niche_taxonomy id=27.
--   2. UPDATE all niche_id / FK rows 13|19|20 → 27.
--   3. UPDATE profiles.creator_niche_id 5|13 → 4; deactivate creator rows 5,13.
--   4. Merge junction + carousel rows onto creator_niche 4.
--   5. DELETE legacy 13, 19, 20 from niche_taxonomy.
--
-- Companion code: two_axis_taxonomy.py, profile_niches.py, profileNiches.ts,
-- corpus_ingest.py (niche 13 gates → 27).

BEGIN;

-- ── 1. New legacy ingest bucket ─────────────────────────────────────
INSERT INTO niche_taxonomy (id, name_vn, name_en, signal_hashtags)
VALUES (
  27,
  'Đời sống · Tâm sự',
  'lifestyle_storytelling',
  ARRAY[
    '#vlog', '#dailylife', '#morningroutine', '#eveningroutine',
    '#lifestylevietnam', '#tam su', '#tamsu', '#doi song',
    '#pov', '#ke chuyen', '#routine', '#mot ngay',
    '#hai', '#haihuoc', '#comedy', '#cuoivoibui', '#sketch', '#sitcom',
    '#reactvideo', '#meme', '#parody', '#skit',
    '#thucung', '#meoviet', '#choviet', '#petcare', '#petlover',
    '#noithat', '#homedecor', '#roomtour', '#trangtrinhacua', '#diyhome'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  name_vn = EXCLUDED.name_vn,
  name_en = EXCLUDED.name_en,
  signal_hashtags = EXCLUDED.signal_hashtags;

SELECT setval(
  'niche_taxonomy_id_seq',
  GREATEST(27, (SELECT COALESCE(MAX(id), 1) FROM niche_taxonomy))
);

-- ── 2. Rebadge legacy niche_id 13 / 19 / 20 → 27 ───────────────────
UPDATE video_corpus
SET niche_id = 27
WHERE niche_id IN (13, 19, 20);

UPDATE video_corpus
SET inferred_creator_niche_id = 4
WHERE inferred_creator_niche_id IN (5, 13);

UPDATE hashtag_niche_map SET niche_id = 27 WHERE niche_id IN (13, 19, 20);

-- Analytics: drop source rows (weekly batch repopulates). Avoids UNIQUE
-- (niche_id, hook_type, week_start) collisions when merging 13+19+20 → 27.
DELETE FROM signal_grades WHERE niche_id IN (13, 19, 20);
DELETE FROM hook_effectiveness WHERE niche_id IN (13, 19, 20);

DELETE FROM creator_velocity
 WHERE niche_id = 19
   AND creator_handle IN (SELECT creator_handle FROM creator_velocity WHERE niche_id = 13);
DELETE FROM creator_velocity
 WHERE niche_id = 20
   AND creator_handle IN (
     SELECT creator_handle FROM creator_velocity WHERE niche_id IN (13, 19)
   );
UPDATE creator_velocity SET niche_id = 27 WHERE niche_id IN (13, 19, 20);
UPDATE daily_ritual SET niche_id = 27 WHERE niche_id IN (13, 19, 20);

DO $migrate$
BEGIN
  IF to_regclass('public.corpus_ingest_queue') IS NOT NULL THEN
    UPDATE public.corpus_ingest_queue
    SET niche_id = 27
    WHERE niche_id IN (13, 19, 20);
  END IF;
END
$migrate$;

UPDATE chat_sessions SET niche_id = 27 WHERE niche_id IN (13, 19, 20);
UPDATE answer_sessions SET niche_id = 27 WHERE niche_id IN (13, 19, 20);
UPDATE niche_candidates SET assigned_niche_id = 27 WHERE assigned_niche_id IN (13, 19, 20);
UPDATE draft_scripts SET niche_id = 27 WHERE niche_id IN (13, 19, 20);
DELETE FROM trend_velocity WHERE niche_id IN (13, 19, 20);
DELETE FROM format_lifecycle WHERE niche_id IN (13, 19, 20);

DO $migrate$
BEGIN
  IF to_regclass('public.competitor_tracking') IS NOT NULL THEN
    UPDATE public.competitor_tracking
    SET niche_id = 27
    WHERE niche_id IN (13, 19, 20);
  END IF;
  IF to_regclass('public.creator_pattern') IS NOT NULL THEN
    UPDATE public.creator_pattern
    SET niche_id = 27
    WHERE niche_id IN (13, 19, 20);
  END IF;
  IF to_regclass('public.niche_insights') IS NOT NULL THEN
    DELETE FROM public.niche_insights WHERE niche_id IN (13, 19, 20);
  END IF;
  IF to_regclass('public.niche_daily_sounds') IS NOT NULL THEN
    DELETE FROM public.niche_daily_sounds WHERE niche_id IN (13, 19, 20);
  END IF;
  IF to_regclass('public.niche_weekly_digest') IS NOT NULL THEN
    DELETE FROM public.niche_weekly_digest WHERE niche_id IN (13, 19, 20);
  END IF;
  IF to_regclass('public.niche_channel_benchmarks') IS NOT NULL THEN
    UPDATE public.niche_channel_benchmarks
    SET niche_id = 27
    WHERE niche_id IN (13, 19, 20);
  END IF;
END
$migrate$;

-- Nightly/batch aggregates — drop source rows (cron repopulates niche 27).
DELETE FROM scene_intelligence WHERE niche_id IN (13, 19, 20);
DELETE FROM cross_creator_patterns WHERE niche_id IN (13, 19, 20);
DELETE FROM trending_sounds WHERE niche_id IN (13, 19, 20);
DELETE FROM trending_cards WHERE niche_id IN (13, 19, 20);

DELETE FROM starter_creators
 WHERE niche_id = 19
   AND handle IN (SELECT handle FROM starter_creators WHERE niche_id = 13);
DELETE FROM starter_creators
 WHERE niche_id = 20
   AND handle IN (SELECT handle FROM starter_creators WHERE niche_id IN (13, 19));
UPDATE starter_creators SET niche_id = 27 WHERE niche_id IN (13, 19, 20);

-- ── 3. UX axis: profiles + deactivate retired creator_niches ─────────
UPDATE profiles SET creator_niche_id = 4 WHERE creator_niche_id IN (5, 13);

UPDATE creator_niches SET
  active = FALSE,
  description_vn = '(Đã gộp vào Đời sống · Tâm sự)'
WHERE id IN (5, 13);

UPDATE creator_niches SET
  description_vn = 'Vlog, tâm sự, POV đời sống, hài relatable, thú cưng, decor nhà — một ngách thay cho Hài & Thú cưng cũ.',
  display_order = 40
WHERE id = 4;

-- ── 4. Junction: lifestyle absorbs comedy + pets_home video axes ─────
INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
SELECT 4, content_class_id, BOOL_OR(is_primary)
FROM creator_niche_content_classes
WHERE creator_niche_id IN (5, 13)
GROUP BY content_class_id
ON CONFLICT (creator_niche_id, content_class_id) DO UPDATE SET
  is_primary = EXCLUDED.is_primary;

INSERT INTO creator_niche_content_classes (creator_niche_id, content_class_id, is_primary)
VALUES
  (4, 24, FALSE),  -- comedy_skit_scripted (browse under lifestyle)
  (4, 25, FALSE),  -- comedy_parody
  (4, 27, FALSE),  -- comedy_react
  (4, 28, FALSE),  -- music_dance_performance (relatable entertainment)
  (4, 29, FALSE),  -- music_dance_choreography
  (4, 69, FALSE),  -- pets_cute_compilation
  (4, 70, FALSE),  -- pets_care_tips
  (4, 71, FALSE),  -- pets_training
  (4, 72, FALSE),  -- pets_owner_storytelling
  (4, 73, FALSE),  -- home_decor_inspiration
  (4, 74, FALSE)   -- home_renovation_diy
ON CONFLICT (creator_niche_id, content_class_id) DO NOTHING;

DELETE FROM creator_niche_content_classes
WHERE creator_niche_id IN (5, 13);

-- ── 5. Legacy → creator map (ingest + backfill) ───────────────────────
CREATE OR REPLACE FUNCTION map_legacy_niche_to_creator_niche(legacy_id INTEGER)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT CASE legacy_id
    WHEN 1  THEN 9
    WHEN 2  THEN 1
    WHEN 3  THEN 2
    WHEN 4  THEN 3
    WHEN 5  THEN 9
    WHEN 6  THEN 4
    WHEN 7  THEN 6
    WHEN 8  THEN 14
    WHEN 9  THEN 8
    WHEN 10 THEN 16
    WHEN 11 THEN 7
    WHEN 12 THEN 9
    WHEN 13 THEN 4   -- Hài (retired) → Lifestyle
    WHEN 14 THEN 12
    WHEN 15 THEN 9
    WHEN 16 THEN 11
    WHEN 17 THEN 8
    WHEN 18 THEN 3
    WHEN 19 THEN 4   -- Thú cưng (retired) → Lifestyle
    WHEN 20 THEN 4   -- Nhà cửa (retired) → Lifestyle
    WHEN 21 THEN 11
    WHEN 22 THEN 4   -- K-pop (retired) → Lifestyle
    WHEN 23 THEN 7
    WHEN 24 THEN 9
    WHEN 25 THEN 12
    WHEN 26 THEN 10
    WHEN 27 THEN 4   -- Đời sống · Tâm sự (canonical legacy ingest)
    ELSE NULL
  END;
$$;

-- ── 6. Drop retired legacy taxonomy rows ──────────────────────────────
DELETE FROM niche_taxonomy WHERE id IN (13, 19, 20);

COMMIT;
