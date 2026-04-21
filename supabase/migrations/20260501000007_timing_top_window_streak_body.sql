-- Phase D.2.2 — real body for timing_top_window_streak.
--
-- The C.4.1 stub returned 0 unconditionally, so `FatigueBand` in the
-- Timing report never triggered even when a (day, hour_bucket) had
-- genuinely held its rank for weeks. Same data-dependency pivot as
-- D.2.1 / D.1.5 — compute directly from `video_corpus.created_at`
-- instead of standing up a weekly ranking snapshot.
--
-- Contract: for each of the last 8 weeks [now - 7(k+1)d, now - 7k*d),
-- rank (day, hour_bucket) cells by count(*) DESC (tiebreak sum_views
-- DESC). Keep only the #1 cell per week. Then walk weeks forward from
-- week 0 (most recent) and count how many consecutive weeks' top cell
-- equals (p_day, p_hour_bucket). Stop at the first mismatch.
--
-- Day encoding matches Python's `weekday()` (Mon=0 ... Sun=6) — the
-- Python consumer passes the heatmap grid's day index directly. PG's
-- `ISODOW` (Mon=1 ... Sun=7) is remapped via `- 1`.
--
-- Hour-bucket encoding matches `_bucket_for_hour` in
-- `report_timing_compute.py`: [6-9, 9-12, 12-15, 15-18, 18-20,
-- 20-22, 22-24, 0-3-folded-from-0-6].

CREATE OR REPLACE FUNCTION public.timing_top_window_streak(
  p_niche_id INT,
  p_day INT,
  p_hour_bucket INT
) RETURNS INTEGER
LANGUAGE plpgsql STABLE
SECURITY INVOKER
SET search_path = public
AS $$
DECLARE
  streak INT := 0;
  rec RECORD;
BEGIN
  IF p_day IS NULL OR p_hour_bucket IS NULL OR p_niche_id IS NULL THEN
    RETURN 0;
  END IF;

  FOR rec IN
    WITH weeks AS (
      SELECT generate_series(0, 7) AS week_idx
    ),
    per_week AS (
      SELECT
        w.week_idx,
        ((EXTRACT(ISODOW FROM v.created_at)::INT - 1) % 7) AS dow,
        CASE
          WHEN EXTRACT(HOUR FROM v.created_at) < 6 THEN 7
          WHEN EXTRACT(HOUR FROM v.created_at) < 9 THEN 0
          WHEN EXTRACT(HOUR FROM v.created_at) < 12 THEN 1
          WHEN EXTRACT(HOUR FROM v.created_at) < 15 THEN 2
          WHEN EXTRACT(HOUR FROM v.created_at) < 18 THEN 3
          WHEN EXTRACT(HOUR FROM v.created_at) < 20 THEN 4
          WHEN EXTRACT(HOUR FROM v.created_at) < 22 THEN 5
          ELSE 6
        END AS hour_bucket,
        COUNT(*) AS n,
        COALESCE(SUM(v.views), 0) AS sv
      FROM weeks w
      JOIN public.video_corpus v
        ON v.niche_id = p_niche_id
       AND v.created_at >= now() - ((w.week_idx + 1) * INTERVAL '7 days')
       AND v.created_at <  now() - (w.week_idx       * INTERVAL '7 days')
      GROUP BY w.week_idx,
               ((EXTRACT(ISODOW FROM v.created_at)::INT - 1) % 7),
               CASE
                 WHEN EXTRACT(HOUR FROM v.created_at) < 6 THEN 7
                 WHEN EXTRACT(HOUR FROM v.created_at) < 9 THEN 0
                 WHEN EXTRACT(HOUR FROM v.created_at) < 12 THEN 1
                 WHEN EXTRACT(HOUR FROM v.created_at) < 15 THEN 2
                 WHEN EXTRACT(HOUR FROM v.created_at) < 18 THEN 3
                 WHEN EXTRACT(HOUR FROM v.created_at) < 20 THEN 4
                 WHEN EXTRACT(HOUR FROM v.created_at) < 22 THEN 5
                 ELSE 6
               END
    ),
    ranked AS (
      SELECT
        week_idx, dow, hour_bucket,
        ROW_NUMBER() OVER (
          PARTITION BY week_idx ORDER BY n DESC, sv DESC, dow ASC, hour_bucket ASC
        ) AS rn
      FROM per_week
    )
    SELECT week_idx, dow, hour_bucket
    FROM ranked
    WHERE rn = 1
    ORDER BY week_idx ASC
  LOOP
    IF rec.dow = p_day AND rec.hour_bucket = p_hour_bucket THEN
      streak := streak + 1;
    ELSE
      EXIT;
    END IF;
  END LOOP;

  RETURN streak;
END;
$$;

GRANT EXECUTE ON FUNCTION public.timing_top_window_streak(INT, INT, INT)
  TO authenticated, service_role;

COMMENT ON FUNCTION public.timing_top_window_streak(INT, INT, INT) IS
  'D.2.2 — consecutive weeks at #1 for (day, hour_bucket) over the last '
  '8 weeks of video_corpus.created_at. Ranks cells by count DESC '
  '(tiebreak sum_views DESC, then (dow, hour_bucket) ASC for determinism). '
  'Stops at first mismatch from week 0.';
