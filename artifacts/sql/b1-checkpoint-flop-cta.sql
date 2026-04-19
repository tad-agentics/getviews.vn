-- B.1 checkpoint — `/app/video` flop funnel (run in Supabase SQL editor, service_role or admin).
-- Source: `usage_events` populated by `logUsage()` from the SPA
-- (`video_screen_load` with metadata.mode, `flop_cta_click`).
--
-- Gate (product): ≥ 30% of flop analysis views lead to a flop → script CTA tap.
-- Operational definition: flop_cta_clicks / flop-mode video_screen_loads.

SELECT
  COUNT(*) FILTER (
    WHERE action = 'video_screen_load' AND (metadata ->> 'mode') = 'flop'
  ) AS flop_screen_loads,
  COUNT(*) FILTER (WHERE action = 'flop_cta_click') AS flop_cta_clicks,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE action = 'flop_cta_click')
    / NULLIF(
        COUNT(*) FILTER (
          WHERE action = 'video_screen_load' AND (metadata ->> 'mode') = 'flop'
        ),
        0
      ),
    2
  ) AS pct_cta_per_flop_load
FROM usage_events
WHERE created_at > now() - interval '14 days';

-- Optional — plan narrative: `chat_sessions` with `intent_type = 'shot_list'`
-- opened within 10 minutes after a flop `video_screen_load` (same user).
WITH flop_loads AS (
  SELECT user_id, created_at AS t0
  FROM usage_events
  WHERE action = 'video_screen_load'
    AND (metadata ->> 'mode') = 'flop'
    AND created_at > now() - interval '14 days'
)
SELECT
  COUNT(*) AS flop_loads,
  COUNT(*) FILTER (
    WHERE EXISTS (
      SELECT 1
      FROM chat_sessions s
      WHERE s.user_id = flop_loads.user_id
        AND s.intent_type = 'shot_list'
        AND s.created_at > flop_loads.t0
        AND s.created_at <= flop_loads.t0 + interval '10 minutes'
    )
  ) AS flop_loads_with_shot_list_10m,
  ROUND(
    100.0 * COUNT(*) FILTER (
      WHERE EXISTS (
        SELECT 1
        FROM chat_sessions s
        WHERE s.user_id = flop_loads.user_id
          AND s.intent_type = 'shot_list'
          AND s.created_at > flop_loads.t0
          AND s.created_at <= flop_loads.t0 + interval '10 minutes'
      )
    ) / NULLIF(COUNT(*), 0),
    2
  ) AS pct_shot_list_followup
FROM flop_loads;
