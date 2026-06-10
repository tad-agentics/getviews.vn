-- H-3 (cloud-run audit 2026-06-10): shift-level run marker for /batch/ingest.
--
-- A double-fired shift (cron retry, manual re-run racing the schedule) did
-- not duplicate rows (video_corpus upserts on video_id) but re-ran the full
-- Gemini extraction — doubled spend and last-writer clobber. The batch pod
-- claims (utc_day, shift) before doing work; the second claimant sees the
-- duplicate and exits. Service-role only.

CREATE TABLE IF NOT EXISTS public.corpus_ingest_runs (
  utc_day        DATE NOT NULL,
  ingest_shift   TEXT NOT NULL DEFAULT '',
  started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at   TIMESTAMPTZ,
  aborted_early  BOOLEAN,
  inserted_count INTEGER,
  PRIMARY KEY (utc_day, ingest_shift)
);

ALTER TABLE public.corpus_ingest_runs ENABLE ROW LEVEL SECURITY;
-- no policies: service-role only.
