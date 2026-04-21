-- Phase D.6.9 — ensemble_calls per-call-site attribution.
--
-- Context: D.6.2 added /admin/ensemble-credits which shows EnsembleData's
-- total "used units" per UTC day. That's the authoritative bill but it
-- can't answer "which pipeline stage is burning our units?". This table
-- fills the gap — one row per successful _ensemble_get invocation
-- tagged with the `call_site` contextvar set by the caller (e.g.
-- "corpus_ingest.hashtag_search", "video_diagnosis.post_info").
--
-- Sampling is "all calls" — EnsembleData fires maybe 10k calls per UTC
-- day at peak; 3.6M rows/year fits comfortably in Supabase and lets
-- ad-hoc call-site × endpoint × date slicing work without a MV.
--
-- Service-role insert/select only; no authenticated grants. Admin reads
-- route through /admin/ensemble-call-sites.

CREATE TABLE IF NOT EXISTS public.ensemble_calls (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint     TEXT NOT NULL,
  call_site    TEXT NOT NULL DEFAULT 'unknown',
  request_class TEXT NOT NULL DEFAULT 'user',
  duration_ms  INTEGER,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT ensemble_calls_duration_nonneg
    CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

-- Dashboard group-by: daily spend by call_site (stacked bar).
CREATE INDEX IF NOT EXISTS ensemble_calls_call_site_recent_idx
  ON public.ensemble_calls (call_site, created_at DESC);

-- Secondary: endpoint breakdown per call site (e.g. which ED endpoint
-- did corpus_ingest call most of on 2026-04-20).
CREATE INDEX IF NOT EXISTS ensemble_calls_endpoint_recent_idx
  ON public.ensemble_calls (endpoint, created_at DESC);

COMMENT ON TABLE public.ensemble_calls IS
  'Phase D.6.9 per-call EnsembleData HTTP attribution. service_role '
  'insert/select only. One row per successful _ensemble_get call — '
  'tagged with the call_site contextvar set by the originating helper '
  '(corpus_ingest.*, video_diagnosis.*, creator_enrich.*, etc.). Pair '
  'with /customer/get-used-units for total-spend reconciliation.';

COMMENT ON COLUMN public.ensemble_calls.call_site IS
  'Free-form dotted namespace. Convention: "<module>.<operation>", '
  'e.g. "corpus_ingest.hashtag_search". Unset calls fall through to '
  '"unknown" so the dashboard shows a clear TODO bucket.';

COMMENT ON COLUMN public.ensemble_calls.request_class IS
  'Mirrors the existing _ed_request_class contextvar: "user" (on-demand, '
  'credit-gated) vs "batch" (cron-driven). Pre-existing split gives the '
  'dashboard a second axis without adding a column per caller.';

ALTER TABLE public.ensemble_calls ENABLE ROW LEVEL SECURITY;
-- No policies. service_role bypasses.
