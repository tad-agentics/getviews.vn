-- Phase A · A2 — daily_ritual table.
--
-- Stores the 3 pre-generated TikTok scripts each creator wakes up to. The
-- nightly batch job (cloud-run/getviews_pipeline/morning_ritual.py) writes
-- one row per (user, date); the Home screen reads it on first open of the
-- day. If the row doesn't exist yet, the UI shows a "sắp có" state rather
-- than blocking on a live Gemini call.
--
-- Shape of `scripts` JSONB — a 3-item array, each item:
--   {
--     "hook_type_en":      "pov",               // canonical enum
--     "hook_type_vi":      "POV",               // HOOK_TYPE_VI[en]
--     "title_vi":          "...",               // the actual hook line, ≤90 chars
--     "why_works":         "...",               // 1 Vietnamese sentence, ≤140 chars
--     "retention_est_pct": 68,
--     "shot_count":        4,
--     "length_sec":        34
--   }
--
-- `adequacy` carries the claim_tiers tier name of the grounding corpus slice
-- so the UI can soften retention claims on thin niches.
--
-- `grounded_video_ids` is the audit trail — which videos fed this generation
-- — so we can debug "why did Gemini write this" offline.

CREATE TABLE IF NOT EXISTS daily_ritual (
  user_id              UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  generated_for_date   DATE NOT NULL,
  niche_id             INTEGER NOT NULL REFERENCES niche_taxonomy (id),
  scripts              JSONB NOT NULL,
  adequacy             TEXT NOT NULL DEFAULT 'none'
    CHECK (adequacy IN ('none','reference_pool','basic_citation',
                        'niche_norms','hook_effectiveness','trend_delta')),
  grounded_video_ids   TEXT[] NOT NULL DEFAULT '{}',
  generated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, generated_for_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_ritual_user_latest
  ON daily_ritual (user_id, generated_for_date DESC);

ALTER TABLE daily_ritual ENABLE ROW LEVEL SECURITY;

-- Users read only their own ritual.
CREATE POLICY "Users read own daily_ritual"
  ON daily_ritual FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- No INSERT/UPDATE/DELETE policy — writes happen via service_role from the
-- nightly batch job. service_role bypasses RLS.
