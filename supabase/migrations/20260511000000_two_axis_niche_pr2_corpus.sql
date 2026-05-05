-- Two-axis niche refactor — PR2 of 6.
--
-- Adds ``video_corpus.content_class_id`` (FK → content_classifications)
-- so the analysis layer can group by sharp (topic × format) categories
-- instead of conflating with the UX-facing creator_niches.
--
-- Backfills existing rows via a heuristic SQL function that maps the
-- legacy (niche_id × content_format) pair to the most-appropriate
-- content_class. Imperfect but better than NULL — pre-launch corpus is
-- small and re-classification is cheap to run later via Gemini if needed.
--
-- ── PR2 scope ────────────────────────────────────────────────────────
--
--   1. Add nullable ``video_corpus.content_class_id INTEGER FK``.
--   2. Add SQL function ``map_legacy_corpus_to_content_class(niche_id,
--      content_format)`` — deterministic mapping rules.
--   3. Backfill ``UPDATE video_corpus SET content_class_id = ...``
--      via the function. Pre-launch corpus is small enough for a
--      single-statement UPDATE; partition / loop logic not needed.
--   4. Add CHECK + index for analytical queries.
--
-- Companion code change (separate file in this PR):
--   cloud-run/getviews_pipeline/corpus_ingest.py — assign
--   content_class_id at ingest time using the same mapping logic
--   re-implemented in Python (kept in sync with the SQL function via
--   shared structure; both will be consolidated in PR5 when the
--   analysis pivots to query content_class_id).
--
-- ``niche_id`` column stays — PR6 retires it after PR3-PR5 migrate
-- callers to creator_niches + content_classifications.
--
-- Idempotency: ``ADD COLUMN IF NOT EXISTS``, function uses CREATE OR
-- REPLACE. UPDATE is a no-op on rows that already have non-null
-- content_class_id.

BEGIN;

-- ── 1. Add column ────────────────────────────────────────────────────

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS content_class_id INTEGER
  REFERENCES content_classifications(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_video_corpus_content_class
  ON video_corpus(content_class_id)
  WHERE content_class_id IS NOT NULL;

COMMENT ON COLUMN video_corpus.content_class_id IS
  'Sharp (topic × format) classification for analysis. Set at ingest by corpus_ingest.py; legacy rows backfilled by 20260511000000. Distinct from niche_id (creator-facing UX niche) which is being retired in PR6 of the two-axis refactor.';

-- ── 2. Mapping function (legacy_niche × content_format → content_class) ─

CREATE OR REPLACE FUNCTION map_legacy_corpus_to_content_class(
  p_niche_id INTEGER,
  p_content_format TEXT
) RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT CASE

    -- ── Beauty (legacy 2 → creator_niche 1) ─────────────────────────
    WHEN p_niche_id = 2 AND p_content_format IN ('review','comparison')      THEN 3   -- beauty_product_review
    WHEN p_niche_id = 2 AND p_content_format = 'haul'                        THEN 4   -- beauty_haul
    WHEN p_niche_id = 2 AND p_content_format = 'tutorial'                    THEN 1   -- beauty_skincare_routine
    WHEN p_niche_id = 2 AND p_content_format = 'grwm'                        THEN 2   -- beauty_makeup_tutorial
    WHEN p_niche_id = 2 AND p_content_format IN ('before_after','storytelling','pov') THEN 5  -- beauty_problem_solution
    WHEN p_niche_id = 2                                                      THEN 1   -- default beauty → skincare

    -- ── Fashion (legacy 3 → creator_niche 2) ────────────────────────
    WHEN p_niche_id = 3 AND p_content_format = 'haul'                        THEN 7   -- fashion_haul
    WHEN p_niche_id = 3 AND p_content_format IN ('review','comparison')      THEN 8   -- fashion_accessory_review
    WHEN p_niche_id = 3 AND p_content_format IN ('outfit_transition','highlight','dance') THEN 9  -- fashion_lookbook_montage
    WHEN p_niche_id = 3 AND p_content_format IN ('vlog','storytelling','pov') THEN 10 -- fashion_thrift / lifestyle vlog OR (fall to outfit_styling default)
    WHEN p_niche_id = 3                                                      THEN 6   -- default fashion → outfit_styling

    -- ── Food (legacy 4 → creator_niche 3) ───────────────────────────
    WHEN p_niche_id = 4 AND p_content_format = 'recipe'                      THEN 13  -- food_recipe_tutorial
    WHEN p_niche_id = 4 AND p_content_format = 'mukbang'                     THEN 14  -- food_challenge
    WHEN p_niche_id = 4 AND p_content_format IN ('review','comparison')      THEN 11  -- food_restaurant_review
    WHEN p_niche_id = 4 AND p_content_format IN ('vlog','storytelling','pov') THEN 12 -- food_street_food_vlog
    WHEN p_niche_id = 4                                                      THEN 11  -- default food → restaurant_review

    -- ── Business / Finance (legacy 5,10,15 → creator_niche 9) ──────
    WHEN p_niche_id = 5 AND p_content_format IN ('haul','review','comparison') THEN 49  -- ecommerce_shopee_review
    WHEN p_niche_id = 5 AND p_content_format = 'tutorial'                    THEN 48  -- mmo_affiliate_education
    WHEN p_niche_id = 5 AND p_content_format = 'storytelling'                THEN 47  -- finance_business_story
    WHEN p_niche_id = 5                                                      THEN 48  -- default → mmo_affiliate_education
    WHEN p_niche_id = 10                                                     THEN 51  -- real_estate_listing
    WHEN p_niche_id = 15 AND p_content_format = 'storytelling'               THEN 47  -- finance_business_story
    WHEN p_niche_id = 15 AND p_content_format = 'comparison'                 THEN 46  -- finance_investment
    WHEN p_niche_id = 15                                                     THEN 45  -- default finance → personal_advice

    -- ── Family / Parenting (legacy 7 → creator_niche 6) ─────────────
    WHEN p_niche_id = 7 AND p_content_format = 'comedy_skit'                 THEN 31  -- parenting_mom_humor
    WHEN p_niche_id = 7 AND p_content_format IN ('vlog','storytelling','pov') THEN 30 -- parenting_baby_milestone
    WHEN p_niche_id = 7 AND p_content_format IN ('lesson','tutorial')        THEN 33  -- parenting_tips_advice
    WHEN p_niche_id = 7                                                      THEN 33  -- default parenting → tips

    -- ── Education (legacy 11,23 → creator_niche 7) ──────────────────
    WHEN p_niche_id IN (11,23) AND p_content_format = 'lesson'               THEN 36  -- edu_language_lesson (best guess)
    WHEN p_niche_id IN (11,23) AND p_content_format IN ('tutorial','comparison') THEN 37 -- edu_life_skill
    WHEN p_niche_id IN (11,23) AND p_content_format = 'storytelling'         THEN 38  -- edu_career_advice
    WHEN p_niche_id IN (11,23)                                               THEN 35  -- default edu → academic_explain

    -- ── Tech (legacy 9 → creator_niche 8) ───────────────────────────
    WHEN p_niche_id = 9 AND p_content_format IN ('haul','review','comparison') THEN 40 -- tech_gadget_unboxing
    WHEN p_niche_id = 9 AND p_content_format = 'tutorial'                    THEN 41  -- tech_software_tutorial
    WHEN p_niche_id = 9                                                      THEN 40  -- default tech → gadget_unboxing

    -- ── Gaming (legacy 17 → creator_niche 8) ────────────────────────
    WHEN p_niche_id = 17 AND p_content_format = 'gameplay'                   THEN 42  -- gaming_gameplay
    WHEN p_niche_id = 17 AND p_content_format IN ('review','comparison')     THEN 43  -- gaming_review_commentary
    WHEN p_niche_id = 17                                                     THEN 42  -- default gaming → gameplay

    -- ── Comedy / Hài (legacy 13 → creator_niche 5) ──────────────────
    WHEN p_niche_id = 13 AND p_content_format = 'comedy_skit'                THEN 24  -- comedy_skit_scripted
    WHEN p_niche_id = 13 AND p_content_format = 'dance'                      THEN 29  -- music_dance_choreography
    WHEN p_niche_id = 13 AND p_content_format IN ('storytelling','pov')      THEN 26  -- comedy_observational
    WHEN p_niche_id = 13                                                     THEN 24  -- default → comedy_skit

    -- ── K-pop / Music (legacy 22 retired → creator_niche 5) ─────────
    WHEN p_niche_id = 22 AND p_content_format = 'dance'                      THEN 29  -- music_dance_choreography
    WHEN p_niche_id = 22                                                     THEN 28  -- music_cover_singing

    -- ── Auto (legacy 14,25 → creator_niche 12) ──────────────────────
    WHEN p_niche_id IN (14,25) AND p_content_format IN ('review','comparison') THEN 65 -- auto_car_review
    WHEN p_niche_id IN (14,25) AND p_content_format = 'tutorial'             THEN 67  -- auto_modification
    WHEN p_niche_id IN (14,25) AND p_content_format IN ('vlog','storytelling') THEN 66 -- auto_moto_culture
    WHEN p_niche_id IN (14,25)                                               THEN 65  -- default auto → car_review

    -- ── Travel & Sports (legacy 16,21 → creator_niche 11) ──────────
    WHEN p_niche_id = 16 AND p_content_format = 'lesson'                     THEN 62  -- travel_tips_planning
    WHEN p_niche_id = 16 AND p_content_format IN ('highlight','outfit_transition') THEN 63 -- travel_adventure
    WHEN p_niche_id = 16                                                     THEN 60  -- default travel → destination
    WHEN p_niche_id = 21 AND p_content_format = 'highlight'                  THEN 64  -- sports_event_highlight
    WHEN p_niche_id = 21 AND p_content_format = 'vlog'                       THEN 63  -- travel_adventure (outdoor)
    WHEN p_niche_id = 21                                                     THEN 64  -- default sports → event_highlight

    -- ── Gym / Fitness (legacy 8 → creator_niche 14) ─────────────────
    WHEN p_niche_id = 8 AND p_content_format IN ('vlog','storytelling')      THEN 59  -- fitness_outdoor_running
    WHEN p_niche_id = 8                                                      THEN 56  -- default gym → fitness_gym_tutorial

    -- ── Wellness (legacy 26 → creator_niche 10) ─────────────────────
    WHEN p_niche_id = 26 AND p_content_format IN ('vlog','storytelling')     THEN 55  -- wellness_holistic
    WHEN p_niche_id = 26 AND p_content_format = 'lesson'                     THEN 53  -- wellness_sleep_recovery (or nutrition)
    WHEN p_niche_id = 26                                                     THEN 52  -- default wellness → mindfulness

    -- ── Pets (legacy 19 → creator_niche 13) ─────────────────────────
    WHEN p_niche_id = 19 AND p_content_format = 'tutorial'                   THEN 71  -- pets_training
    WHEN p_niche_id = 19 AND p_content_format = 'lesson'                     THEN 70  -- pets_care_tips
    WHEN p_niche_id = 19 AND p_content_format IN ('storytelling','pov','comedy_skit') THEN 72 -- pets_owner_storytelling
    WHEN p_niche_id = 19                                                     THEN 69  -- default pets → cute_compilation

    -- ── Home (legacy 20 → creator_niche 13) ─────────────────────────
    WHEN p_niche_id = 20 AND p_content_format = 'tutorial'                   THEN 74  -- home_renovation_diy
    WHEN p_niche_id = 20 AND p_content_format IN ('haul','review')           THEN 73  -- home_decor_inspiration (review of decor items)
    WHEN p_niche_id = 20                                                     THEN 73  -- default home → decor_inspiration

    -- ── Retired niches with no special format mapping ───────────────
    WHEN p_niche_id = 1                                                      THEN 49  -- legacy Shopee review → ecommerce_shopee_review
    WHEN p_niche_id = 6                                                      THEN 23  -- legacy Chị đẹp → lifestyle_aesthetic
    WHEN p_niche_id = 12                                                     THEN 50  -- legacy Livestream → ecommerce_live_commerce
    WHEN p_niche_id = 18                                                     THEN 13  -- legacy Nấu ăn → food_recipe_tutorial
    WHEN p_niche_id = 24                                                     THEN 46  -- legacy Crypto → finance_investment

    ELSE NULL
  END;
$$;

COMMENT ON FUNCTION map_legacy_corpus_to_content_class IS
  'Heuristic mapping (legacy niche_id × content_format) → content_classifications.id. Used by PR2 backfill + corpus_ingest.py at ingest time. Stays correct as long as the seeded content_classifications ids in 20260510000000 are stable.';

-- ── 3. Backfill existing rows ────────────────────────────────────────
-- Pre-launch corpus is small; single-statement UPDATE is fine. If
-- corpus grew large, would batch by indexed_at descending.

UPDATE video_corpus
SET content_class_id = map_legacy_corpus_to_content_class(niche_id, content_format)
WHERE content_class_id IS NULL
  AND niche_id IS NOT NULL;

COMMIT;
