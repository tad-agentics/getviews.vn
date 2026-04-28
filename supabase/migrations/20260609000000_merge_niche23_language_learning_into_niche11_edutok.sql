-- Merge niche 23 (Học tiếng / Ngoại ngữ) into niche 11 (EduTok VN).
--
-- Product decision: one education + language-learning bucket. Reuses id 11,
-- rebadges all niche_id = 23 rows to 11, merges signal_hashtags, dedupes
-- hashtag_niche_map, resolves UNIQUE conflicts on a few aggregate tables,
-- clears derived per-niche rolls for 23 (cron rebuilds).
--
-- Post-deploy (ops): SELECT refresh_niche_intelligence(); and allow weekly
-- analytics crons to refill hook_effectiveness, creator_velocity, etc.

BEGIN;

-- ── 1. EduTok VN — union of prior id=11 hashtags + former id=23 pool ─────
UPDATE public.niche_taxonomy SET
  signal_hashtags = ARRAY[
    '#edutokvn', '#hoctienganh', '#giaoduc', '#kienthuc',
    '#hoctot', '#tienganhonline', '#tienganh', '#ielts', '#toeic',
    '#hoctienghan', '#tienghan', '#tiengtrung', '#hoctiengtrung',
    '#kynang', '#kynangsong', '#kynanggiaotiep', '#lichsu', '#khoadan',
    '#tamly', '#sachdoc', '#booktokvn', '#bookreview', '#hoctokyo',
    '#onthitoeic', '#minhhoa', '#hientuong', '#khoahoc', '#toanhoc',
    '#ielts7', '#ielts8', '#ielts9', '#bandscore',
    '#toeic800', '#toeic900', '#cefr', '#cefrb1', '#cefrb2', '#cefrc1',
    '#jlpt', '#jlptn3', '#jlptn2', '#jlptn1', '#topik', '#hsk',
    '#hsk4', '#hsk5', '#hsk6', '#delf', '#dele', '#cambridgeenglish',
    '#pronunciation', '#phatamtienganh', '#phatam', '#tudienenglish',
    '#vocabularybuilder', '#wordoftheday', '#tuvungmoi', '#hoctuvung',
    '#nguphap', '#ngupháptienganh', '#tu_vung_tieng_anh', '#englishidioms',
    '#idiomofday', '#englishphrases', '#cumtu', '#shadowing', '#luyennoi',
    '#luyennghe', '#englishlistening', '#englishspeaking',
    '#hoctienghan_chonguoimoibatdau', '#tienghancoban',
    '#hoctiengnhat_jlpt', '#tiengnhatcoban',
    '#hoctiengtrung_chonguoimoibatdau', '#tiengtrungcoban',
    '#hoctiengphap_coban', '#hoctiengduc', '#hoctiengtaybanha',
    '#polyglot', '#langtok', '#languagetok', '#englishteacher',
    '#nativetutor', '#langlearner', '#duolingostreak', '#tienganhgiaotiep',
    '#tienganhcongviec', '#englishforwork', '#englishforbusiness',
    '#englishforchildren'
  ]
WHERE id = 11;

-- ── 2. Core corpus + profiles ─────────────────────────────────────────────
UPDATE public.video_corpus SET niche_id = 11 WHERE niche_id = 23;

DO $$
BEGIN
  IF to_regclass('public.video_shots') IS NOT NULL THEN
    UPDATE public.video_shots SET niche_id = 11 WHERE niche_id = 23;
  END IF;
END $$;

UPDATE public.profiles SET primary_niche = 11 WHERE primary_niche = 23;

UPDATE public.profiles p
SET niche_ids = deduped.new_ids
FROM (
  SELECT
    p2.id,
    (
      SELECT COALESCE(array_agg(val ORDER BY min_idx), '{}')
      FROM (
        SELECT val, min(idx) AS min_idx
        FROM unnest(array_replace(p2.niche_ids, 23, 11)) WITH ORDINALITY AS t(val, idx)
        GROUP BY val
      ) s
    ) AS new_ids
  FROM public.profiles p2
  WHERE p2.niche_ids IS NOT NULL AND 23 = ANY (p2.niche_ids)
) deduped
WHERE p.id = deduped.id;

UPDATE public.chat_sessions SET niche_id = 11 WHERE niche_id = 23;

-- ── 3. hashtag_niche_map — drop dupes, rebadge ──────────────────────────────
DELETE FROM public.hashtag_niche_map
 WHERE niche_id = 23
   AND hashtag IN (SELECT hashtag FROM public.hashtag_niche_map WHERE niche_id = 11);
UPDATE public.hashtag_niche_map SET niche_id = 11 WHERE niche_id = 23;

-- ── 4. Tables with UNIQUE (niche_id, …): drop conflicting rows first ─────
DELETE FROM public.trending_sounds
 WHERE niche_id = 23
   AND (sound_id, week_of) IN (
     SELECT sound_id, week_of FROM public.trending_sounds WHERE niche_id = 11
   );
UPDATE public.trending_sounds SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.cross_creator_patterns
 WHERE niche_id = 23
   AND (hook_type, week_of) IN (
     SELECT hook_type, week_of FROM public.cross_creator_patterns WHERE niche_id = 11
   );
UPDATE public.cross_creator_patterns SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.scene_intelligence
 WHERE niche_id = 23
   AND scene_type IN (SELECT scene_type FROM public.scene_intelligence WHERE niche_id = 11);
UPDATE public.scene_intelligence SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.channel_formulas
 WHERE niche_id = 23
   AND handle IN (SELECT handle FROM public.channel_formulas WHERE niche_id = 11);
UPDATE public.channel_formulas SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.niche_daily_sounds
 WHERE niche_id = 23
   AND computed_date IN (
     SELECT computed_date FROM public.niche_daily_sounds WHERE niche_id = 11
   );
UPDATE public.niche_daily_sounds SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.niche_weekly_digest
 WHERE niche_id = 23
   AND week_of IN (SELECT week_of FROM public.niche_weekly_digest WHERE niche_id = 11);
UPDATE public.niche_weekly_digest SET niche_id = 11 WHERE niche_id = 23;

-- ── 5. Straight rebases (no composite uniqueness conflict expected) ───────
UPDATE public.daily_ritual SET niche_id = 11 WHERE niche_id = 23;
UPDATE public.trending_cards SET niche_id = 11 WHERE niche_id = 23;
UPDATE public.answer_sessions SET niche_id = 11 WHERE niche_id = 23;
UPDATE public.draft_scripts SET niche_id = 11 WHERE niche_id = 23;
UPDATE public.niche_candidates SET assigned_niche_id = 11 WHERE assigned_niche_id = 23;
UPDATE public.trend_velocity SET niche_id = 11 WHERE niche_id = 23;
UPDATE public.format_lifecycle SET niche_id = 11 WHERE niche_id = 23;

UPDATE public.competitor_tracking SET niche_id = 11 WHERE niche_id = 23;
UPDATE public.creator_pattern SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.creator_velocity
 WHERE niche_id = 23
   AND creator_handle IN (SELECT creator_handle FROM public.creator_velocity WHERE niche_id = 11);
UPDATE public.creator_velocity SET niche_id = 11 WHERE niche_id = 23;

DELETE FROM public.signal_grades
 WHERE niche_id = 23
   AND (hook_type, week_start) IN (
     SELECT hook_type, week_start FROM public.signal_grades WHERE niche_id = 11
   );
UPDATE public.signal_grades SET niche_id = 11 WHERE niche_id = 23;

-- ── 6. Derived rolls — clear 23; pipelines rebuild ─────────────────────────
DELETE FROM public.hook_effectiveness WHERE niche_id = 23;
DELETE FROM public.niche_insights WHERE niche_id = 23;
DELETE FROM public.starter_creators WHERE niche_id = 23;

-- ── 7. Drop merged niche from taxonomy ────────────────────────────────────
DELETE FROM public.niche_taxonomy WHERE id = 23;

COMMIT;
