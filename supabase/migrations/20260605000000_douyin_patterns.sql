-- 2026-06-05 — D5a — Kho Douyin · weekly pattern signals.
--
-- Per design pack ``screens/douyin.jsx`` § I — "3 cards / niche / week"
-- pattern signals surfaced ABOVE the §II video grid. Each card is a
-- named pattern (hook template + format signal) clustered weekly from
-- the niche's Douyin corpus by the D5b Gemini synthesizer.
--
-- This is intentionally a flatter shape than ``video_patterns`` (the
-- VN TikTok signature-clustering table). The Douyin corpus is small
-- (~1.5K rows max) and refreshes weekly, so we don't need a separate
-- signature_hash → instances graph — Gemini sees the whole niche
-- corpus in one prompt and emits 3 named patterns directly. The
-- ``sample_video_ids`` array carries the corpus rows that anchor each
-- pattern; the FE joins back to ``douyin_video_corpus`` for thumbnails
-- + metrics.
--
-- Field provenance:
--   • niche_id, week_of   — orchestrator (D5c) computes the ISO week
--                          start (Mon 00:00 UTC) and writes one batch
--                          of 3 rows per niche per week.
--   • name_vn / name_zh   — Gemini D5b output (pattern title in VN
--                          and the closest Chinese phrasing).
--   • hook_template_vi    — Gemini D5b — fill-in-the-blank VN hook
--                          template, e.g. "3 việc trước khi ___".
--   • format_signal_vi    — Gemini D5b — one-sentence summary of the
--                          editing / pacing / framing signature.
--   • sample_video_ids    — Gemini D5b — 2-5 anchor video_ids from
--                          ``douyin_video_corpus.video_id`` that best
--                          embody the pattern.
--   • cn_rise_pct_avg     — orchestrator computes the mean
--                          ``cn_rise_pct`` across the sample videos
--                          (NULL when none have a delta yet).
--   • computed_at         — timestamp of the synth run; D5c uses this
--                          + ``week_of`` to short-circuit re-runs.
--
-- Cron: weekly Mondays 04:00 VN (= 21:00 Sun UTC), staggered after the
-- daily ingest (05:00 VN) and synth (06:00 VN) crons. The week's
-- ``week_of`` is the ISO Monday start of the synth run.

-- ── Schema ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS douyin_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  niche_id INTEGER NOT NULL REFERENCES douyin_niche_taxonomy (id) ON DELETE CASCADE,

  -- ISO Monday 00:00 UTC of the synth week. Stored as a DATE rather
  -- than TIMESTAMPTZ so equality joins / dedupe queries don't have
  -- to deal with timezone arithmetic. The synth run computes this
  -- via ``date_trunc('week', now() AT TIME ZONE 'UTC')::date``.
  week_of DATE NOT NULL,

  -- 1-based ordinal within the (niche, week) batch — rank by signal
  -- strength as the synthesizer ordered them. Always 1, 2, or 3.
  rank SMALLINT NOT NULL CHECK (rank BETWEEN 1 AND 3),

  -- Pattern naming + content (Gemini D5b output).
  name_vn           TEXT NOT NULL,
  name_zh           TEXT,
  hook_template_vi  TEXT NOT NULL,
  format_signal_vi  TEXT NOT NULL,

  -- Anchor sample of corpus video_ids (2-5 rows). Stored as a
  -- TEXT[] instead of an FK array because the corpus row may be
  -- pruned later — we don't want pattern-card writes to cascade.
  sample_video_ids TEXT[] NOT NULL,

  -- Aggregate strength signal (avg cn_rise_pct of the sample). NULL
  -- when none of the sample rows have a delta yet (Douyin corpus is
  -- still seeding the second snapshot).
  cn_rise_pct_avg REAL,

  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Exactly one row per (niche, week, rank) — the orchestrator
  -- upserts via ``ON CONFLICT (niche_id, week_of, rank)``.
  UNIQUE (niche_id, week_of, rank)
);

-- ── Indexes ─────────────────────────────────────────────────────────

-- Primary read path: "give me the 3 patterns for niche N this week".
CREATE INDEX IF NOT EXISTS idx_douyin_patterns_niche_week
  ON douyin_patterns (niche_id, week_of DESC, rank ASC);

-- Synth-orchestrator's "what week did we last compute for this niche"
-- short-circuit query.
CREATE INDEX IF NOT EXISTS idx_douyin_patterns_week_computed
  ON douyin_patterns (week_of DESC, computed_at DESC);

-- ── RLS ─────────────────────────────────────────────────────────────

ALTER TABLE douyin_patterns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read douyin_patterns"
  ON douyin_patterns FOR SELECT
  TO authenticated
  USING (true);

-- Service-role only for INSERT / UPDATE / DELETE (the weekly cron is
-- the only writer). Default policy denies anon writes; no explicit
-- write policy needed because no policy ⇒ no access.

-- ── Comments ────────────────────────────────────────────────────────

COMMENT ON TABLE douyin_patterns IS
  'D5a (2026-06-05) — Weekly Kho Douyin pattern signals (3 cards/niche/week). Synthesised by ``cloud-run/getviews_pipeline/douyin_patterns_synth.py`` (D5b) and orchestrated by the weekly /batch/douyin-patterns cron (D5c). Service-role writes only.';

COMMENT ON COLUMN douyin_patterns.week_of IS
  'ISO Monday 00:00 UTC of the synth week. Stored DATE so equality joins are TZ-safe. Compute via date_trunc(''week'', now() AT TIME ZONE ''UTC'')::date.';

COMMENT ON COLUMN douyin_patterns.rank IS
  '1-based ordinal within the (niche, week) batch. Synthesiser orders by perceived signal strength; FE renders the cards in this order.';

COMMENT ON COLUMN douyin_patterns.hook_template_vi IS
  'Gemini D5b — fill-in-the-blank VN hook template. Example: "3 việc trước khi ___" with the blank as a literal "___" or "[X]" marker.';

COMMENT ON COLUMN douyin_patterns.format_signal_vi IS
  'Gemini D5b — 1-sentence summary of the format/edit/pacing signature shared by the sample videos.';

COMMENT ON COLUMN douyin_patterns.sample_video_ids IS
  'Anchor sample of Douyin video_ids (2-5 entries from ``douyin_video_corpus.video_id``). Not a hard FK — preserved across corpus prune.';

COMMENT ON COLUMN douyin_patterns.cn_rise_pct_avg IS
  'Mean ``cn_rise_pct`` across the sample videos. NULL when the corpus has yet to accumulate a second snapshot delta for the sample.';
