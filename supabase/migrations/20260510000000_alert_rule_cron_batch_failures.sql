-- 2026-05-10 — alert rule: cron_batch_failures.
--
-- Closes the Axis 5 loop from state-of-corpus.md: today we WRITE
-- failure rows to batch_job_runs via record_job_run (PR #113), but
-- nothing READS them. A silent cron failure is invisible until
-- someone eyeballs the dashboard.
--
-- This rule fires on any batch_job_runs row with status='failed' in
-- the last 7 days. Threshold is 0 on purpose — pipeline failures
-- are rare enough that even one should page. Adjust
-- threshold_json.failures_max higher if the alert turns noisy.
--
-- Evaluator: cloud-run/getviews_pipeline/routers/admin.py
--            _evaluate_cron_batch_failures (registered in
--            _EVALUATORS dict in the same file).
--
-- Dedup lives in admin_alert_fires: only transitions cleared→firing
-- generate a new fire row (and Slack post). Sustained breaches do
-- not re-page.

INSERT INTO public.admin_alert_rules (rule_key, label, severity, threshold_json)
VALUES (
  'cron_batch_failures',
  'Pipeline cron có failures trong 7 ngày qua',
  'warn',
  '{"failures_max": 0, "window_days": 7}'::jsonb
)
ON CONFLICT (rule_key) DO NOTHING;
