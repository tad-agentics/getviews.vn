-- Align timing_top_window_streak with Python heatmap: event time =
-- COALESCE(posted_at, indexed_at, created_at), bucketed in Asia/Ho_Chi_Minh
-- (same wall-clock semantics as report_timing_compute.build_heatmap_grid).

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
    corpus_evt AS (
      SELECT
        w.week_idx,
        COALESCE(v.posted_at, v.indexed_at, v.created_at) AS evt,
        v.views
      FROM weeks w
      INNER JOIN public.video_corpus v
        ON v.niche_id = p_niche_id
       AND COALESCE(v.posted_at, v.indexed_at, v.created_at) >= now() - ((w.week_idx + 1) * INTERVAL '7 days')
       AND COALESCE(v.posted_at, v.indexed_at, v.created_at) <  now() - (w.week_idx       * INTERVAL '7 days')
    ),
    per_week AS (
      SELECT
        week_idx,
        ((EXTRACT(ISODOW FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh'))::INT - 1) % 7) AS dow,
        CASE
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 6 THEN 7
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 9 THEN 0
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 12 THEN 1
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 15 THEN 2
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 18 THEN 3
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 20 THEN 4
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 22 THEN 5
          ELSE 6
        END AS hour_bucket,
        COUNT(*) AS n,
        COALESCE(SUM(views), 0) AS sv
      FROM corpus_evt
      GROUP BY week_idx,
        ((EXTRACT(ISODOW FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh'))::INT - 1) % 7),
        CASE
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 6 THEN 7
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 9 THEN 0
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 12 THEN 1
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 15 THEN 2
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 18 THEN 3
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 20 THEN 4
          WHEN EXTRACT(HOUR FROM (evt AT TIME ZONE 'Asia/Ho_Chi_Minh')) < 22 THEN 5
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
  'Consecutive weeks at #1 for (day, hour_bucket). Uses '
  'COALESCE(posted_at, indexed_at, created_at) windowed like the Python heatmap; '
  'dow/hour buckets in Asia/Ho_Chi_Minh.';
