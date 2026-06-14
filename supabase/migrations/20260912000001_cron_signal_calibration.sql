-- Weekly signal calibration job (2026-06-14) — learns viral-score weights +
-- per-lever predictive rho from corpus outcomes.

SELECT cron.schedule(
  'cron-batch-signal-calibration',
  '0 20 * * 0',
  $cmd$
  SELECT net.http_post(
    url := (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_api_url')
      || '/batch/signal-calibration',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Batch-Secret', (SELECT decrypted_secret FROM vault.decrypted_secrets WHERE name = 'cloud_run_batch_secret')
    ),
    body := '{}'::jsonb,
    timeout_milliseconds := 3540000
  );
  $cmd$
);

INSERT INTO public.expected_cron_jobs (jobname, note) VALUES
  ('cron-batch-signal-calibration', 'Sun 20:00 — outcome-driven viral-score weight calibration')
ON CONFLICT (jobname) DO NOTHING;
