-- Content-class corpus pivot — Phase 0: provenance columns, ingest targets, ACQE state, upsert RPC.

BEGIN;

-- ── video_corpus provenance ─────────────────────────────────────────────
ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS ingest_loop_niche_id INTEGER,
  ADD COLUMN IF NOT EXISTS ingest_loop_content_class_id INTEGER,
  ADD COLUMN IF NOT EXISTS class_assignment_tier TEXT,
  ADD COLUMN IF NOT EXISTS class_assignment_disagreement DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS score_cohort_mismatch BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN video_corpus.ingest_loop_niche_id IS
  'Legacy niche_taxonomy.id at batch loop time (before HI-11 route).';
COMMENT ON COLUMN video_corpus.ingest_loop_content_class_id IS
  'Predicted content_class_id at pre-score time (Phase 2 cohort).';
COMMENT ON COLUMN video_corpus.class_assignment_tier IS
  'ACQE tier: validated | flagged | low_conf | NULL.';
COMMENT ON COLUMN video_corpus.class_assignment_disagreement IS
  '0–1 disagreement between hashtag map v2, Gemini, and pre-score class.';
COMMENT ON COLUMN video_corpus.score_cohort_mismatch IS
  'True when instructiveness scored on a different cohort than stored class.';

CREATE INDEX IF NOT EXISTS idx_video_corpus_ingest_loop_niche
  ON video_corpus (ingest_loop_niche_id)
  WHERE ingest_loop_niche_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_video_corpus_ingest_loop_content_class
  ON video_corpus (ingest_loop_content_class_id)
  WHERE ingest_loop_content_class_id IS NOT NULL;

-- ── content_class_ingest_targets (Phase 3 loop; seeded Phase 0) ─────────
CREATE TABLE IF NOT EXISTS content_class_ingest_targets (
  content_class_id INTEGER PRIMARY KEY
    REFERENCES content_classifications(id) ON DELETE CASCADE,
  signal_hashtags TEXT[] NOT NULL DEFAULT '{}',
  daily_vpn INTEGER NOT NULL DEFAULT 15,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  priority INTEGER NOT NULL DEFAULT 0,
  viability_tier TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE content_class_ingest_targets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages content class ingest targets"
  ON content_class_ingest_targets;
CREATE POLICY "Service role manages content class ingest targets"
  ON content_class_ingest_targets
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Authenticated read content class ingest targets"
  ON content_class_ingest_targets;
CREATE POLICY "Authenticated read content class ingest targets"
  ON content_class_ingest_targets
  FOR SELECT
  TO authenticated
  USING (true);

GRANT SELECT ON content_class_ingest_targets TO authenticated;
GRANT ALL ON content_class_ingest_targets TO service_role;

-- Seed one row per content_classifications (ACQE adjusts active/vpn nightly).
INSERT INTO content_class_ingest_targets (content_class_id, signal_hashtags, daily_vpn, active, priority)
SELECT cc.id, '{}'::TEXT[], 15, TRUE, 0
FROM content_classifications cc
ON CONFLICT (content_class_id) DO NOTHING;

-- ── ACQE run state (single row) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS acqe_run_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  run_count INTEGER NOT NULL DEFAULT 0,
  last_run_at TIMESTAMPTZ,
  cold_start_complete BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE acqe_run_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role manages acqe run state" ON acqe_run_state;
CREATE POLICY "Service role manages acqe run state"
  ON acqe_run_state
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

INSERT INTO acqe_run_state (id, run_count, cold_start_complete)
VALUES (1, 0, FALSE)
ON CONFLICT (id) DO NOTHING;

-- ── upsert_video_corpus_batch — provenance + class re-upsert (Phase 3) ───
DROP FUNCTION IF EXISTS upsert_video_corpus_batch(jsonb);

CREATE OR REPLACE FUNCTION upsert_video_corpus_batch(
    p_rows JSONB
)
RETURNS TABLE (out_video_id TEXT, out_action TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
#variable_conflict use_variable
DECLARE
    r JSONB;
    v_video_id TEXT;
    v_existing_cc INTEGER;
    v_new_cc INTEGER;
BEGIN
    FOR r IN SELECT * FROM jsonb_array_elements(p_rows)
    LOOP
        v_video_id := r->>'video_id';
        v_new_cc := NULLIF(r->>'content_class_id', '')::INTEGER;

        SELECT content_class_id INTO v_existing_cc
        FROM video_corpus
        WHERE video_id = v_video_id;

        INSERT INTO video_corpus (
            video_id, content_type, niche_id, content_class_id, creator_handle, tiktok_url,
            thumbnail_url, video_url, frame_urls, analysis_json,
            views, likes, comments, shares, engagement_rate,
            indexed_at,
            ingest_source, first_seen_at, last_refreshed_at, quality_tier,
            niche_resolution_source, niche_resolution_confidence, inferred_creator_niche_id,
            ingest_loop_niche_id, ingest_loop_content_class_id,
            class_assignment_tier, class_assignment_disagreement, score_cohort_mismatch
        )
        VALUES (
            v_video_id,
            COALESCE(r->>'content_type', 'video'),
            (r->>'niche_id')::INTEGER,
            v_new_cc,
            COALESCE(r->>'creator_handle', ''),
            COALESCE(r->>'tiktok_url', ''),
            r->>'thumbnail_url',
            r->>'video_url',
            COALESCE((r->'frame_urls')::TEXT::TEXT[], '{}'),
            COALESCE(r->'analysis_json', '{}'),
            COALESCE((r->>'views')::BIGINT, 0),
            COALESCE((r->>'likes')::BIGINT, 0),
            COALESCE((r->>'comments')::BIGINT, 0),
            COALESCE((r->>'shares')::BIGINT, 0),
            COALESCE((r->>'engagement_rate')::NUMERIC, 0),
            COALESCE((r->>'indexed_at')::TIMESTAMPTZ, now()),
            COALESCE(r->>'ingest_source', 'batch_nightly'),
            COALESCE((r->>'first_seen_at')::TIMESTAMPTZ, now()),
            now(),
            COALESCE(r->>'quality_tier', 'high'),
            r->>'niche_resolution_source',
            NULLIF(r->>'niche_resolution_confidence', '')::DOUBLE PRECISION,
            NULLIF(r->>'inferred_creator_niche_id', '')::INTEGER,
            NULLIF(r->>'ingest_loop_niche_id', '')::INTEGER,
            NULLIF(r->>'ingest_loop_content_class_id', '')::INTEGER,
            r->>'class_assignment_tier',
            NULLIF(r->>'class_assignment_disagreement', '')::DOUBLE PRECISION,
            COALESCE((r->>'score_cohort_mismatch')::BOOLEAN, FALSE)
        )
        ON CONFLICT (video_id) DO UPDATE SET
            content_type        = EXCLUDED.content_type,
            niche_id            = EXCLUDED.niche_id,
            content_class_id    = EXCLUDED.content_class_id,
            creator_handle      = EXCLUDED.creator_handle,
            tiktok_url          = EXCLUDED.tiktok_url,
            thumbnail_url       = COALESCE(EXCLUDED.thumbnail_url, video_corpus.thumbnail_url),
            video_url           = COALESCE(EXCLUDED.video_url, video_corpus.video_url),
            frame_urls          = EXCLUDED.frame_urls,
            analysis_json       = EXCLUDED.analysis_json,
            views               = EXCLUDED.views,
            likes               = EXCLUDED.likes,
            comments            = EXCLUDED.comments,
            shares              = EXCLUDED.shares,
            engagement_rate     = EXCLUDED.engagement_rate,
            indexed_at          = EXCLUDED.indexed_at,
            ingest_source       = COALESCE(video_corpus.ingest_source, EXCLUDED.ingest_source),
            first_seen_at       = COALESCE(video_corpus.first_seen_at, EXCLUDED.first_seen_at),
            last_refreshed_at   = now(),
            quality_tier        = COALESCE(video_corpus.quality_tier, EXCLUDED.quality_tier),
            niche_resolution_source      = EXCLUDED.niche_resolution_source,
            niche_resolution_confidence  = EXCLUDED.niche_resolution_confidence,
            inferred_creator_niche_id    = EXCLUDED.inferred_creator_niche_id,
            ingest_loop_niche_id         = COALESCE(EXCLUDED.ingest_loop_niche_id, video_corpus.ingest_loop_niche_id),
            ingest_loop_content_class_id = COALESCE(EXCLUDED.ingest_loop_content_class_id, video_corpus.ingest_loop_content_class_id),
            class_assignment_tier        = COALESCE(EXCLUDED.class_assignment_tier, video_corpus.class_assignment_tier),
            class_assignment_disagreement = COALESCE(EXCLUDED.class_assignment_disagreement, video_corpus.class_assignment_disagreement),
            score_cohort_mismatch        = EXCLUDED.score_cohort_mismatch;

        RETURN QUERY SELECT v_video_id, 'upserted'::TEXT;
    END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION upsert_video_corpus_batch(JSONB) TO service_role;

COMMENT ON FUNCTION upsert_video_corpus_batch(JSONB) IS
  'Provenance-safe batch upsert. Updates content_class_id + ingest_loop_* on conflict (Phase 3 class dedup).';

COMMIT;
