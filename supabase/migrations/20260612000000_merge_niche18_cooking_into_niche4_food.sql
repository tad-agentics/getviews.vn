-- Merge niche 18 (Nấu ăn / Công thức) into niche 4 (Review đồ ăn / F&B).
--
-- Single umbrella for dining-out reviews, F&B, and home cooking / recipes.
-- Reuses id 4; rebadges niche_id = 18 → 4; merges signal_hashtags;
-- dedupes hashtag_niche_map; resolves UNIQUE conflicts; clears aggregates for 18.
--
-- Post-deploy: SELECT refresh_niche_intelligence(); and let weekly analytics refill.

BEGIN;

-- ── 1. Ẩm thực & Ăn uống — union id=4 + former id=18 hashtag pools ─────────
UPDATE public.niche_taxonomy SET
  name_vn = 'Ẩm thực & Ăn uống',
  name_en = 'Food, recipes & dining',
  signal_hashtags = ARRAY[
    '#reviewdoan', '#angi', '#foodtiktok', '#ancungtiktok', '#reviewanngon',
    '#foodreview', '#anngon', '#doananh', '#quananngon', '#reviewquan',
    '#nhahang', '#cafehanoi', '#cafesaigon', '#cafedep', '#cafevietnam',
    '#travelfood', '#streetfood', '#monngon', '#nau an', '#nauan',
    '#doanngon', '#comtam', '#pho', '#banhmi', '#reviewcafe',
    '#reviewrestaurant', '#foodie', '#yummy', '#banhngot', '#trachen',
    '#smoothie', '#nauanngon', '#congthucnauan', '#nauanmoiday', '#buacomgiadinh',
    '#monngonmoingay', '#daubepper', '#nauanhanoi', '#nauansaigon', '#recipevietnam',
    '#cookingtutorial', '#nauanfacebook', '#congthucmoingay', '#amthucviet', '#nauancungcon',
    '#monchay', '#nauanchay', '#anlanh', '#chefvietnam', '#homecooking',
    '#mealprep', '#benhnaunan', '#nauankhoe', '#combinh', '#nauantaigia',
    '#amthucvietnam', '#monngondagia', '#monngonhangngay', '#monnhanhdongian', '#moncanh',
    '#moncuon', '#monkho', '#monchien', '#monxao', '#monbun',
    '#monpho', '#monmien', '#monmy', '#banhxeo', '#che',
    '#chenong', '#chegiolanh', '#trangmieng', '#dokho', '#dongan',
    '#caytrai', '#buacomme', '#buatoi', '#buasang', '#buatrua',
    '#monanbaby', '#anansangkhong', '#cachamcon', '#foodievn', '#vietnameserecipe',
    '#asiancooking', '#vietnamesecooking', '#nauanonline', '#chiase_congthuc', '#congthucdonhan',
    '#nauanbackoc', '#nauancongso', '#mealprep_viet', '#batonbubao'
  ]
WHERE id = 4;

-- ── 2. Core corpus + profiles ───────────────────────────────────────────────
UPDATE public.video_corpus SET niche_id = 4 WHERE niche_id = 18;

DO $$
BEGIN
  IF to_regclass('public.video_shots') IS NOT NULL THEN
    UPDATE public.video_shots SET niche_id = 4 WHERE niche_id = 18;
  END IF;
END $$;

UPDATE public.profiles SET primary_niche = 4 WHERE primary_niche = 18;

-- LATERAL avoids a correlated scalar subquery inside the FROM-subquery SELECT list
-- (some Postgres deployments error “syntax error at or near p2” on that pattern).
UPDATE public.profiles AS p
SET niche_ids = agg.new_ids
FROM public.profiles AS p2,
LATERAL (
  SELECT COALESCE(array_agg(val ORDER BY min_idx), '{}'::integer[]) AS new_ids
  FROM (
    SELECT val, min(idx) AS min_idx
    FROM unnest(array_replace(p2.niche_ids, 18, 4)) WITH ORDINALITY AS t(val, idx)
    GROUP BY val
  ) s
) AS agg
WHERE p.id = p2.id
  AND p2.niche_ids IS NOT NULL
  AND 18 = ANY (p2.niche_ids);

UPDATE public.chat_sessions SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.hashtag_niche_map
 WHERE niche_id = 18
   AND hashtag IN (SELECT hashtag FROM public.hashtag_niche_map WHERE niche_id = 4);
UPDATE public.hashtag_niche_map SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.trending_sounds
 WHERE niche_id = 18
   AND (sound_id, week_of) IN (
     SELECT sound_id, week_of FROM public.trending_sounds WHERE niche_id = 4
   );
UPDATE public.trending_sounds SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.cross_creator_patterns
 WHERE niche_id = 18
   AND (hook_type, week_of) IN (
     SELECT hook_type, week_of FROM public.cross_creator_patterns WHERE niche_id = 4
   );
UPDATE public.cross_creator_patterns SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.scene_intelligence
 WHERE niche_id = 18
   AND scene_type IN (SELECT scene_type FROM public.scene_intelligence WHERE niche_id = 4);
UPDATE public.scene_intelligence SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.channel_formulas
 WHERE niche_id = 18
   AND handle IN (SELECT handle FROM public.channel_formulas WHERE niche_id = 4);
UPDATE public.channel_formulas SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.niche_daily_sounds
 WHERE niche_id = 18
   AND computed_date IN (
     SELECT computed_date FROM public.niche_daily_sounds WHERE niche_id = 4
   );
UPDATE public.niche_daily_sounds SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.niche_weekly_digest
 WHERE niche_id = 18
   AND week_of IN (SELECT week_of FROM public.niche_weekly_digest WHERE niche_id = 4);
UPDATE public.niche_weekly_digest SET niche_id = 4 WHERE niche_id = 18;

UPDATE public.daily_ritual SET niche_id = 4 WHERE niche_id = 18;
UPDATE public.trending_cards SET niche_id = 4 WHERE niche_id = 18;
UPDATE public.answer_sessions SET niche_id = 4 WHERE niche_id = 18;
UPDATE public.draft_scripts SET niche_id = 4 WHERE niche_id = 18;
UPDATE public.niche_candidates SET assigned_niche_id = 4 WHERE assigned_niche_id = 18;
UPDATE public.trend_velocity SET niche_id = 4 WHERE niche_id = 18;
UPDATE public.format_lifecycle SET niche_id = 4 WHERE niche_id = 18;

UPDATE public.competitor_tracking SET niche_id = 4 WHERE niche_id = 18;
UPDATE public.creator_pattern SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.creator_velocity
 WHERE niche_id = 18
   AND creator_handle IN (SELECT creator_handle FROM public.creator_velocity WHERE niche_id = 4);
UPDATE public.creator_velocity SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.signal_grades
 WHERE niche_id = 18
   AND (hook_type, week_start) IN (
     SELECT hook_type, week_start FROM public.signal_grades WHERE niche_id = 4
   );
UPDATE public.signal_grades SET niche_id = 4 WHERE niche_id = 18;

DELETE FROM public.hook_effectiveness WHERE niche_id = 18;
DELETE FROM public.niche_insights WHERE niche_id = 18;
DELETE FROM public.starter_creators WHERE niche_id = 18;

DELETE FROM public.niche_taxonomy WHERE id = 18;

COMMIT;
