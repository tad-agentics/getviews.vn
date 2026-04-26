-- 2026-05-30 — pattern decks: structure / why / careful / angles columns on
-- ``video_patterns`` so PatternModal on /app/trends can render the design's
-- full-deck content (``screens/trends.jsx`` lines 652-946) instead of the
-- "Đang chuẩn bị" stubs PR-T4 shipped.
--
-- The per-pattern deck is produced by a nightly Gemini synthesizer that
-- reads the pattern's top videos as grounding context and emits:
--
--   ``structure``  — JSONB string[] of 4 lines describing
--                    Hook / Setup / Body / Payoff timing + intent.
--   ``why``        — TEXT, ~1-2 sentence explanation of why the
--                    pattern works (audience psychology + algorithm).
--   ``careful``    — TEXT, ~1 sentence warning about pitfalls /
--                    over-use / authenticity drop-off.
--   ``angles``     — JSONB array of {angle, filled, gap?}. Each
--                    entry is a content angle creators have used
--                    inside this pattern; ``filled`` is an integer
--                    count of corpus videos using that angle;
--                    ``gap: true`` flags angles no creator has
--                    covered yet — the high-signal opportunity
--                    surface in the modal.
--   ``deck_computed_at`` — TIMESTAMPTZ stamp. Synth job re-runs only
--                    when this is null OR older than the freshness
--                    window (≥ 7 days, mirrors channel_formulas).
--
-- All four content columns default to NULL so existing pattern rows
-- stay valid. ``PatternModal.tsx`` already renders "Đang chuẩn bị"
-- stubs when these fields are null — no FE break before the
-- synthesizer's first run.
--
-- The synthesizer + batch endpoint live in
-- ``cloud-run/getviews_pipeline/pattern_deck_synth.py`` and
-- ``/batch/pattern-decks`` respectively. The pg_cron schedule lands
-- in a sibling doc-only migration (see
-- ``20260530000001_pg_cron_pattern_decks.sql``).

ALTER TABLE public.video_patterns
  ADD COLUMN IF NOT EXISTS structure         JSONB,
  ADD COLUMN IF NOT EXISTS why               TEXT,
  ADD COLUMN IF NOT EXISTS careful           TEXT,
  ADD COLUMN IF NOT EXISTS angles            JSONB,
  ADD COLUMN IF NOT EXISTS deck_computed_at  TIMESTAMPTZ;

-- Partial index for the synth-orchestrator's "what's stale?" query.
-- Most rows are stale (or never decked) at any given moment, so a
-- partial index keeps the cost low.
CREATE INDEX IF NOT EXISTS video_patterns_deck_stale_idx
  ON public.video_patterns (deck_computed_at NULLS FIRST)
  WHERE is_active = TRUE;
