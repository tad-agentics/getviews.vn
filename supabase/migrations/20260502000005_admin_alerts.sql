-- Phase D.6.10 — admin alert evaluation state.
--
-- The D.6.2 credits panel colors runway <7d in red but doesn't actually
-- page anyone. This migration sets up the state storage for a cron
-- evaluator that runs every 15 minutes, checks a small set of rules
-- against the existing admin_* tables + the EnsembleData used-units
-- endpoint, and fires a Slack webhook when a rule crosses its
-- threshold for the first time (deduplicated via the fires table
-- below so a sustained breach doesn't spam the channel).
--
-- Schema:
--   admin_alert_rules   — declarative rule catalog (name, evaluator,
--                         threshold config). Seeded with three rules
--                         below. Extend by INSERTing a new row via
--                         service_role; no code redeploy needed for
--                         plain-threshold rule changes.
--
--   admin_alert_fires   — one row per (rule, severity) that transitioned
--                         into the breached state. The evaluator only
--                         fires when the current tick is breached and
--                         the last row for that (rule) is non-existent
--                         or cleared (dedup).

CREATE TABLE IF NOT EXISTS public.admin_alert_rules (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_key       TEXT NOT NULL UNIQUE,
  label          TEXT NOT NULL,
  severity       TEXT NOT NULL DEFAULT 'warn',
  threshold_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  enabled        BOOLEAN NOT NULL DEFAULT true,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT admin_alert_rules_severity_valid
    CHECK (severity IN ('info', 'warn', 'crit'))
);

CREATE TABLE IF NOT EXISTS public.admin_alert_fires (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_key     TEXT NOT NULL REFERENCES public.admin_alert_rules(rule_key)
                 ON UPDATE CASCADE ON DELETE CASCADE,
  severity     TEXT NOT NULL,
  message      TEXT NOT NULL,
  context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- "firing" when the rule first breached; "cleared" when the next
  -- evaluation shows it's no longer breached. The evaluator only emits
  -- a webhook on a `firing` row (or on `cleared` if the operator opts
  -- in via a per-rule flag — not implemented yet).
  phase        TEXT NOT NULL DEFAULT 'firing',
  delivered_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT admin_alert_fires_phase_valid
    CHECK (phase IN ('firing', 'cleared'))
);

CREATE INDEX IF NOT EXISTS admin_alert_fires_rule_recent_idx
  ON public.admin_alert_fires (rule_key, created_at DESC);

COMMENT ON TABLE public.admin_alert_rules IS
  'Phase D.6.10 alert rule catalog. The cron-admin-alerts Edge Function '
  'iterates these rules, evaluates each via a matching Python evaluator '
  '(keyed on rule_key in cloud-run or Deno equivalent), and writes to '
  'admin_alert_fires on state transitions.';

COMMENT ON TABLE public.admin_alert_fires IS
  'Phase D.6.10 alert fire history + state. The most-recent row per '
  'rule_key represents the current state: phase=firing means breached, '
  'phase=cleared means back under threshold.';

ALTER TABLE public.admin_alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_alert_fires ENABLE ROW LEVEL SECURITY;
-- No policies; service_role only.

-- Seed three starter rules. Adjust thresholds via UPDATE without a
-- redeploy; new rules need matching evaluator code shipped alongside.

INSERT INTO public.admin_alert_rules (rule_key, label, severity, threshold_json)
VALUES
  (
    'ensemble_runway_low',
    'EnsembleData monthly runway <7 ngày',
    'crit',
    '{"runway_days_max": 7}'::jsonb
  ),
  (
    'corpus_stale',
    'Corpus chưa ingest trong 48h',
    'warn',
    '{"hours_since_last_ingest": 48}'::jsonb
  ),
  (
    'admin_trigger_error_spike',
    'Trigger error rate > 50% trong 10 lần gần nhất',
    'warn',
    '{"window_runs": 10, "error_pct_max": 50}'::jsonb
  )
ON CONFLICT (rule_key) DO NOTHING;
