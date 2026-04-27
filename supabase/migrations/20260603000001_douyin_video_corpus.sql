-- 2026-06-03 — D1 — Kho Douyin · video corpus table.
--
-- Mirrors ``video_corpus`` (the Vietnamese TikTok corpus) for Douyin videos.
-- Separate table per the Option A schema decision:
--   - Douyin has fields TikTok doesn't (title_zh, title_vi, sub_vi,
--     adapt_level, eta_weeks_*, cn_rise_pct, translator_notes).
--   - TikTok has fields Douyin doesn't need (Vietnamese-context tone /
--     dialect, caption with VN hashtags).
--   - Cleaner FK scoping for ``douyin_video_shots`` (separate cascade
--     boundary than VN ``video_shots``).
--   - Easier to debug + revert if Douyin's metadata shape diverges from
--     TikTok's (EnsembleData normalises both, but D2 may discover edge
--     cases that we'd otherwise have to retrofit into VN queries).
--
-- Field provenance (where each value comes from):
--   • Identity / metrics — EnsembleData /douyin/post/info aweme_detail
--     (D2 ``parse_douyin_metadata``).
--   • Analysis JSON — Gemini extraction via the existing ``analyze_aweme``
--     pipeline (platform-agnostic — Wave 2.5 PR #6 enrichment fields
--     work on Douyin aweme dicts unchanged).
--   • title_zh / hashtags_zh — Douyin caption + tags (raw CN).
--   • title_vi — Gemini Chinese→Vietnamese translation pass (D2).
--   • sub_vi — short ≤120-char VN gloss for the card (D3).
--   • adapt_level / adapt_reason / eta_weeks_* — Gemini cultural-distance
--     synthesis (D3). Caveat: human review pending; D3 surfaces a flag
--     for that on the FE.
--   • cn_rise_pct — derived from EnsembleData metrics deltas over time
--     (D2 falls back to NULL until we have multiple ingest snapshots).
--   • translator_notes — JSONB array of {tag, note} rows (D3).

-- ── Schema ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS douyin_video_corpus (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Douyin video identity. ``video_id`` is the Douyin aweme_id (numeric
  -- string). Treated as the natural key for upsert dedupe.
  video_id TEXT NOT NULL UNIQUE,
  douyin_url TEXT NOT NULL,
  content_type TEXT NOT NULL CHECK (content_type IN ('video', 'carousel')),

  niche_id INTEGER NOT NULL REFERENCES douyin_niche_taxonomy (id),

  -- Creator (denormalized — Douyin profile lookup is an extra ED call).
  creator_handle TEXT NOT NULL,
  creator_name TEXT,
  creator_followers BIGINT,

  -- Media URLs. ``video_url`` is the playable file (from EnsembleData);
  -- ``thumbnail_url`` is the poster; ``frame_urls`` mirrors the VN corpus
  -- pattern (R2-hosted scene frames extracted at ingest time).
  thumbnail_url TEXT,
  video_url TEXT,
  frame_urls TEXT[] NOT NULL DEFAULT '{}',

  -- Gemini analysis (full JSON — same shape as VN corpus).
  analysis_json JSONB NOT NULL,

  -- Engagement (Douyin emphasises ``saves`` strongly — algorithm signal).
  views BIGINT NOT NULL DEFAULT 0,
  likes BIGINT NOT NULL DEFAULT 0,
  comments BIGINT NOT NULL DEFAULT 0,
  shares BIGINT NOT NULL DEFAULT 0,
  saves BIGINT NOT NULL DEFAULT 0,
  engagement_rate NUMERIC(10, 4) NOT NULL DEFAULT 0,

  -- Posting metadata (when did the creator publish).
  posted_at TIMESTAMPTZ,
  video_duration REAL,

  -- Hook + format (mirror of VN corpus enrichment).
  hook_type TEXT,
  hook_phrase TEXT,
  content_format TEXT,
  cta_type TEXT,

  -- Douyin-specific surface fields. Filled progressively across PRs:
  --   D2 → title_zh, title_vi, hashtags_zh
  --   D3 → sub_vi, adapt_level, adapt_reason, eta_weeks_min/max,
  --         cn_rise_pct, translator_notes
  -- Nullable so D2 ingest can land rows before D3 synth runs.
  title_zh TEXT,
  title_vi TEXT,
  sub_vi TEXT,
  hashtags_zh TEXT[],

  adapt_level TEXT CHECK (adapt_level IS NULL OR adapt_level IN ('green', 'yellow', 'red')),
  adapt_reason TEXT,
  eta_weeks_min INTEGER,
  eta_weeks_max INTEGER,
  cn_rise_pct REAL,
  translator_notes JSONB,

  -- Synth bookkeeping (mirrors video_patterns.deck_computed_at) so a
  -- nightly cron can re-grade only stale rows in D3.
  synth_computed_at TIMESTAMPTZ
);

-- ── Indexes ─────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_douyin_corpus_niche_indexed
  ON douyin_video_corpus (niche_id, indexed_at DESC);

CREATE INDEX IF NOT EXISTS idx_douyin_corpus_niche_views
  ON douyin_video_corpus (niche_id, views DESC);

CREATE INDEX IF NOT EXISTS idx_douyin_corpus_niche_adapt
  ON douyin_video_corpus (niche_id, adapt_level)
  WHERE adapt_level IS NOT NULL;

-- Stale-rows partial index for the D3 synth cron (mirrors
-- video_patterns_deck_stale_idx pattern).
CREATE INDEX IF NOT EXISTS idx_douyin_corpus_synth_stale
  ON douyin_video_corpus (synth_computed_at NULLS FIRST);

-- ── RLS ─────────────────────────────────────────────────────────────

ALTER TABLE douyin_video_corpus ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read douyin_video_corpus"
  ON douyin_video_corpus FOR SELECT
  TO authenticated
  USING (true);

-- Service-role only for INSERT/UPDATE — the daily ingest cron is the
-- only writer. Mirrors video_corpus' write policy.

COMMENT ON TABLE douyin_video_corpus IS
  'D1 (2026-06-03) — Kho Douyin video corpus. Mirrors video_corpus for the Douyin pipeline (D2 ingest fills creator/metrics/analysis, D3 synth fills adapt_level + translator_notes + eta_weeks_*). Service-role writes only.';

COMMENT ON COLUMN douyin_video_corpus.video_id IS
  'Douyin aweme_id (numeric string). Natural key for upsert dedupe — the daily ingest UPSERT ON CONFLICT (video_id).';

COMMENT ON COLUMN douyin_video_corpus.adapt_level IS
  'D3 — green/yellow/red cultural-distance grade (Gemini-scored). NULL until synth runs. FE shows "human review pending" caveat below the chip.';

COMMENT ON COLUMN douyin_video_corpus.translator_notes IS
  'D3 — JSONB array of {tag: TEXT, note: TEXT} entries (e.g. [{tag: "BỐI CẢNH", note: "..."}, ...]). Drives the modal''s NOTE VĂN HOÁ · DỊCH GIẢ section.';

COMMENT ON COLUMN douyin_video_corpus.cn_rise_pct IS
  'D2/D3 — % growth in views over the prior 7d window. NULL on first ingest (no prior snapshot); populated once we have a re-ingest delta.';
