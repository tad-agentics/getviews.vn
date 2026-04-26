-- PR-2 Studio Home — channel diagnostic restructure.
--
-- Adds typed strengths + weaknesses JSONB columns to the channel_formulas
-- cache. Each item carries title/metric/why/action/bridge_to per the
-- design pack's MyChannelCard §C/§D blocks. The legacy ``lessons`` column
-- stays in place — fresh runs synthesize a lessons[] from strengths so
-- existing FE consumers (InsightsFooter, ChannelScreen) keep rendering.
--
-- Cache rows pre-PR-2 retain ``strengths = []`` / ``weaknesses = []``;
-- the FE detects empty arrays and hides the diagnostic blocks until the
-- row's 7-day TTL expires and a fresh Gemini run repopulates them.

ALTER TABLE public.channel_formulas
  ADD COLUMN IF NOT EXISTS strengths  JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS weaknesses JSONB NOT NULL DEFAULT '[]'::jsonb;
