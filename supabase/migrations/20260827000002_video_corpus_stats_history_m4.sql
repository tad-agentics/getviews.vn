-- Phase 2b / §4.7 M4 — stats time-series + distribution_shape on video_corpus.

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS stats_history jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS distribution_shape text NULL;

COMMENT ON COLUMN video_corpus.stats_history IS
  '§4.7 M4 — [{ "at", "phase", "views", "likes", "comments", "shares" }, …] ingest t0 + refetch t6h/t24h';
COMMENT ON COLUMN video_corpus.distribution_shape IS
  '§4.7 M4 — null | spike_then_flat (derived when stats_history complete)';

CREATE INDEX IF NOT EXISTS video_corpus_first_seen_at_idx
  ON video_corpus (first_seen_at DESC)
  WHERE tiktok_url IS NOT NULL AND tiktok_url <> '';

-- Extend upsert_video_corpus_batch: persist initial stats_history on insert;
-- preserve existing history on conflict (M4 refetch owns updates thereafter).
DROP FUNCTION IF EXISTS upsert_video_corpus_batch(jsonb);

CREATE OR REPLACE FUNCTION upsert_video_corpus_batch(p_rows JSONB)
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
            video_id, content_type, content_class_id, creator_handle, tiktok_url,
            thumbnail_url, video_url, frame_urls, analysis_json,
            views, likes, comments, shares, engagement_rate,
            indexed_at,
            ingest_source, first_seen_at, last_refreshed_at, quality_tier,
            niche_resolution_source, niche_resolution_confidence, inferred_creator_niche_id,
            ingest_loop_niche_id, ingest_loop_content_class_id,
            class_assignment_tier, class_assignment_disagreement, score_cohort_mismatch,
            stats_history
        )
        VALUES (
            v_video_id,
            COALESCE(r->>'content_type', 'video'),
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
            COALESCE((r->>'score_cohort_mismatch')::BOOLEAN, FALSE),
            COALESCE(r->'stats_history', '[]'::jsonb)
        )
        ON CONFLICT (video_id) DO UPDATE SET
            content_type        = EXCLUDED.content_type,
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
            score_cohort_mismatch        = EXCLUDED.score_cohort_mismatch,
            stats_history = CASE
                WHEN jsonb_array_length(COALESCE(video_corpus.stats_history, '[]'::jsonb)) = 0
                THEN COALESCE(EXCLUDED.stats_history, '[]'::jsonb)
                ELSE video_corpus.stats_history
            END;

        RETURN QUERY SELECT v_video_id, 'upserted'::TEXT;
    END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION upsert_video_corpus_batch(JSONB) TO service_role;

COMMENT ON FUNCTION upsert_video_corpus_batch(JSONB) IS
  'Phase C batch upsert + M4 stats_history (preserve on conflict).';
