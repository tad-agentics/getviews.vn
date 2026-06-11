-- Retire content_class 69 (pets_cute_compilation / Pet cute / funny).
-- Stops class-loop ingest + browse; re-homes existing corpus rows.

UPDATE content_classifications
SET active = FALSE
WHERE id = 69;

UPDATE content_class_ingest_targets
SET active = FALSE, daily_vpn = 0, updated_at = now()
WHERE content_class_id = 69;

DELETE FROM creator_niche_content_classes
WHERE content_class_id = 69;

DELETE FROM hashtag_class_map
WHERE content_class_id = 69;

UPDATE video_corpus
SET
  content_class_id = 23,
  ingest_loop_content_class_id = CASE
    WHEN ingest_loop_content_class_id = 69 THEN 23
    ELSE ingest_loop_content_class_id
  END
WHERE content_class_id = 69
   OR ingest_loop_content_class_id = 69;

-- Legacy pets (niche 19) default → pets_owner_storytelling (72), not retired 69.
CREATE OR REPLACE FUNCTION map_legacy_corpus_to_content_class(
  p_niche_id INTEGER,
  p_content_format TEXT
) RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT CASE
    WHEN p_niche_id = 2 AND p_content_format IN ('review','comparison')      THEN 3
    WHEN p_niche_id = 2 AND p_content_format = 'haul'                        THEN 4
    WHEN p_niche_id = 2 AND p_content_format = 'tutorial'                    THEN 1
    WHEN p_niche_id = 2 AND p_content_format = 'grwm'                        THEN 2
    WHEN p_niche_id = 2 AND p_content_format IN ('before_after','storytelling','pov') THEN 5
    WHEN p_niche_id = 2                                                      THEN 1
    WHEN p_niche_id = 3 AND p_content_format = 'haul'                        THEN 7
    WHEN p_niche_id = 3 AND p_content_format IN ('review','comparison')      THEN 8
    WHEN p_niche_id = 3 AND p_content_format IN ('outfit_transition','highlight','dance') THEN 9
    WHEN p_niche_id = 3 AND p_content_format IN ('vlog','storytelling','pov') THEN 10
    WHEN p_niche_id = 3                                                      THEN 6
    WHEN p_niche_id = 4 AND p_content_format = 'recipe'                      THEN 13
    WHEN p_niche_id = 4 AND p_content_format = 'mukbang'                     THEN 14
    WHEN p_niche_id = 4 AND p_content_format IN ('review','comparison')      THEN 11
    WHEN p_niche_id = 4 AND p_content_format IN ('vlog','storytelling','pov') THEN 12
    WHEN p_niche_id = 4                                                      THEN 11
    WHEN p_niche_id = 5 AND p_content_format IN ('haul','review','comparison') THEN 49
    WHEN p_niche_id = 5 AND p_content_format = 'tutorial'                    THEN 48
    WHEN p_niche_id = 5 AND p_content_format = 'storytelling'                THEN 47
    WHEN p_niche_id = 5                                                      THEN 48
    WHEN p_niche_id = 10                                                     THEN 51
    WHEN p_niche_id = 15 AND p_content_format = 'storytelling'               THEN 47
    WHEN p_niche_id = 15 AND p_content_format = 'comparison'                 THEN 46
    WHEN p_niche_id = 15                                                     THEN 45
    WHEN p_niche_id = 7 AND p_content_format = 'comedy_skit'                 THEN 31
    WHEN p_niche_id = 7 AND p_content_format IN ('vlog','storytelling','pov') THEN 30
    WHEN p_niche_id = 7 AND p_content_format IN ('lesson','tutorial')        THEN 33
    WHEN p_niche_id = 7                                                      THEN 33
    WHEN p_niche_id IN (11,23) AND p_content_format = 'lesson'               THEN 36
    WHEN p_niche_id IN (11,23) AND p_content_format IN ('tutorial','comparison') THEN 37
    WHEN p_niche_id IN (11,23) AND p_content_format = 'storytelling'         THEN 38
    WHEN p_niche_id IN (11,23)                                               THEN 35
    WHEN p_niche_id = 9 AND p_content_format IN ('haul','review','comparison') THEN 40
    WHEN p_niche_id = 9 AND p_content_format = 'tutorial'                    THEN 41
    WHEN p_niche_id = 9                                                      THEN 40
    WHEN p_niche_id = 17 AND p_content_format = 'gameplay'                   THEN 42
    WHEN p_niche_id = 17 AND p_content_format IN ('review','comparison')     THEN 43
    WHEN p_niche_id = 17                                                     THEN 42
    WHEN p_niche_id = 13 AND p_content_format = 'comedy_skit'                THEN 24
    WHEN p_niche_id = 13 AND p_content_format = 'dance'                      THEN 29
    WHEN p_niche_id = 13 AND p_content_format IN ('storytelling','pov')      THEN 26
    WHEN p_niche_id = 13                                                     THEN 24
    WHEN p_niche_id = 22 AND p_content_format = 'dance'                      THEN 29
    WHEN p_niche_id = 22                                                     THEN 28
    WHEN p_niche_id IN (14,25) AND p_content_format IN ('review','comparison') THEN 65
    WHEN p_niche_id IN (14,25) AND p_content_format = 'tutorial'             THEN 67
    WHEN p_niche_id IN (14,25) AND p_content_format IN ('vlog','storytelling') THEN 66
    WHEN p_niche_id IN (14,25)                                               THEN 65
    WHEN p_niche_id = 16 AND p_content_format = 'lesson'                     THEN 62
    WHEN p_niche_id = 16 AND p_content_format IN ('highlight','outfit_transition') THEN 63
    WHEN p_niche_id = 16                                                     THEN 60
    WHEN p_niche_id = 21 AND p_content_format = 'highlight'                  THEN 64
    WHEN p_niche_id = 21 AND p_content_format = 'vlog'                       THEN 63
    WHEN p_niche_id = 21                                                     THEN 64
    WHEN p_niche_id = 8 AND p_content_format IN ('vlog','storytelling')      THEN 59
    WHEN p_niche_id = 8                                                      THEN 56
    WHEN p_niche_id = 26 AND p_content_format IN ('vlog','storytelling')     THEN 55
    WHEN p_niche_id = 26 AND p_content_format = 'lesson'                     THEN 53
    WHEN p_niche_id = 26                                                     THEN 52
    WHEN p_niche_id = 19 AND p_content_format = 'tutorial'                   THEN 71
    WHEN p_niche_id = 19 AND p_content_format = 'lesson'                     THEN 70
    WHEN p_niche_id = 19 AND p_content_format IN ('storytelling','pov','comedy_skit') THEN 72
    WHEN p_niche_id = 19                                                     THEN 72
    WHEN p_niche_id = 20 AND p_content_format = 'tutorial'                   THEN 74
    WHEN p_niche_id = 20 AND p_content_format IN ('haul','review')           THEN 73
    WHEN p_niche_id = 20                                                     THEN 73
    WHEN p_niche_id = 1                                                      THEN 49
    WHEN p_niche_id = 6                                                      THEN 23
    WHEN p_niche_id = 12                                                     THEN 50
    WHEN p_niche_id = 18                                                     THEN 13
    WHEN p_niche_id = 24                                                     THEN 46
    ELSE NULL
  END;
$$;
