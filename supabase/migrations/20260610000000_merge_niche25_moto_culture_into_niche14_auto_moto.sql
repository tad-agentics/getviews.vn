-- Merge niche 25 (Xe máy / Moto culture) into niche 14 (Ô tô / Xe máy).
--
-- Single bucket for cars + motorcycle lifestyle / touring / community content.
-- Reuses id 14; rebadges niche_id = 25 → 14; merges signal_hashtags;
-- dedupes hashtag_niche_map; resolves UNIQUE conflicts; clears aggregates for 25.
--
-- Post-deploy: SELECT refresh_niche_intelligence(); and let weekly analytics refill.

BEGIN;

-- ── 1. Ô tô / Xe máy — union id=14 + former id=25 hashtag pools ───────────
UPDATE public.niche_taxonomy SET
  signal_hashtags = ARRAY[
    '#oto', '#xemay', '#reviewxe', '#otovietnam',
    '#car', '#motorvietnam', '#xe', '#drivervietnam',
    '#reviewoto', '#xedien', '#evcar', '#vinfast',
    '#honda', '#yamaha', '#suzuki', '#piaggio',
    '#vespa', '#sh', '#airblade', '#exciter',
    '#baodong xe', '#reviewxemay', '#moto', '#supermoto',
    '#xe dap dien', '#phutung xe', '#doixe', '#muaxe',
    '#motovlogvietnam', '#motorlife', '#bikerlife',
    '#motorcyclelife', '#twowheels', '#twowheellife',
    '#ridevietnam', '#phuottren2banh', '#phuotxemay',
    '#duongmonhochiminh', '#truongsonduong', '#qua_deo',
    '#detehadi', '#dieukhienxenhanh',
    '#anhem2banh', '#dauthecodo', '#groupride',
    '#tourxemay', '#hoixemoto', '#hoiyeuxe',
    '#camerahanhtrinh', '#actioncam', '#gopromoto',
    '#dolexemay', '#donoixe', '#custommoto',
    '#caferacervietnam', '#bobbervietnam', '#scramblervietnam',
    '#hondamonkey', '#hondavietnam', '#motonhapkhau',
    '#pkl', '#xemoto', '#bigbike',
    '#bigbikevietnam', '#kawasaki', '#ducati',
    '#bmwmotorrad', '#harleydavidson', '#triumph',
    '#trackday', '#trackdayvietnam', '#duaxe',
    '#duaxehanoi', '#sport_riding', '#wheelie',
    '#wheelievietnam', '#stuntridingvietnam',
    '#exciter150', '#exciter155', '#raider150',
    '#satria', '#winner_x', '#cb150',
    '#z1000', '#mt07', '#mt09',
    '#r3vietnam', '#r6', '#cbr150r',
    '#tracer', '#nmax', '#xmax',
    '#vario', '#airblade150', '#sh125'
  ]
WHERE id = 14;

-- ── 2. Core corpus + profiles ─────────────────────────────────────────────
UPDATE public.video_corpus SET niche_id = 14 WHERE niche_id = 25;

DO $$
BEGIN
  IF to_regclass('public.video_shots') IS NOT NULL THEN
    UPDATE public.video_shots SET niche_id = 14 WHERE niche_id = 25;
  END IF;
END $$;

UPDATE public.profiles SET primary_niche = 14 WHERE primary_niche = 25;

UPDATE public.profiles p
SET niche_ids = deduped.new_ids
FROM (
  SELECT
    p2.id,
    (
      SELECT COALESCE(array_agg(val ORDER BY min_idx), '{}')
      FROM (
        SELECT val, min(idx) AS min_idx
        FROM unnest(array_replace(p2.niche_ids, 25, 14)) WITH ORDINALITY AS t(val, idx)
        GROUP BY val
      ) s
    ) AS new_ids
  FROM public.profiles p2
  WHERE p2.niche_ids IS NOT NULL AND 25 = ANY (p2.niche_ids)
) deduped
WHERE p.id = deduped.id;

UPDATE public.chat_sessions SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.hashtag_niche_map
 WHERE niche_id = 25
   AND hashtag IN (SELECT hashtag FROM public.hashtag_niche_map WHERE niche_id = 14);
UPDATE public.hashtag_niche_map SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.trending_sounds
 WHERE niche_id = 25
   AND (sound_id, week_of) IN (
     SELECT sound_id, week_of FROM public.trending_sounds WHERE niche_id = 14
   );
UPDATE public.trending_sounds SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.cross_creator_patterns
 WHERE niche_id = 25
   AND (hook_type, week_of) IN (
     SELECT hook_type, week_of FROM public.cross_creator_patterns WHERE niche_id = 14
   );
UPDATE public.cross_creator_patterns SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.scene_intelligence
 WHERE niche_id = 25
   AND scene_type IN (SELECT scene_type FROM public.scene_intelligence WHERE niche_id = 14);
UPDATE public.scene_intelligence SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.channel_formulas
 WHERE niche_id = 25
   AND handle IN (SELECT handle FROM public.channel_formulas WHERE niche_id = 14);
UPDATE public.channel_formulas SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.niche_daily_sounds
 WHERE niche_id = 25
   AND computed_date IN (
     SELECT computed_date FROM public.niche_daily_sounds WHERE niche_id = 14
   );
UPDATE public.niche_daily_sounds SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.niche_weekly_digest
 WHERE niche_id = 25
   AND week_of IN (SELECT week_of FROM public.niche_weekly_digest WHERE niche_id = 14);
UPDATE public.niche_weekly_digest SET niche_id = 14 WHERE niche_id = 25;

UPDATE public.daily_ritual SET niche_id = 14 WHERE niche_id = 25;
UPDATE public.trending_cards SET niche_id = 14 WHERE niche_id = 25;
UPDATE public.answer_sessions SET niche_id = 14 WHERE niche_id = 25;
UPDATE public.draft_scripts SET niche_id = 14 WHERE niche_id = 25;
UPDATE public.niche_candidates SET assigned_niche_id = 14 WHERE assigned_niche_id = 25;
UPDATE public.trend_velocity SET niche_id = 14 WHERE niche_id = 25;
UPDATE public.format_lifecycle SET niche_id = 14 WHERE niche_id = 25;

UPDATE public.competitor_tracking SET niche_id = 14 WHERE niche_id = 25;
UPDATE public.creator_pattern SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.creator_velocity
 WHERE niche_id = 25
   AND creator_handle IN (SELECT creator_handle FROM public.creator_velocity WHERE niche_id = 14);
UPDATE public.creator_velocity SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.signal_grades
 WHERE niche_id = 25
   AND (hook_type, week_start) IN (
     SELECT hook_type, week_start FROM public.signal_grades WHERE niche_id = 14
   );
UPDATE public.signal_grades SET niche_id = 14 WHERE niche_id = 25;

DELETE FROM public.hook_effectiveness WHERE niche_id = 25;
DELETE FROM public.niche_insights WHERE niche_id = 25;
DELETE FROM public.starter_creators WHERE niche_id = 25;

DELETE FROM public.niche_taxonomy WHERE id = 25;

COMMIT;
