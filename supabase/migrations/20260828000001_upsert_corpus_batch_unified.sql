-- Unify upsert_video_corpus_batch: M4 stats_history + ingest criteria + breakout fields.
-- M4 migration (20260827000002) regressed boost/relax columns from 20260730000000.
-- Batch ingest now uses provenance merge + full PostgREST upsert; this RPC stays
-- parity-safe for any direct callers.

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
    v_new_cc INTEGER;
BEGIN
    FOR r IN SELECT * FROM jsonb_array_elements(p_rows)
    LOOP
        v_video_id := r->>'video_id';
        v_new_cc := NULLIF(r->>'content_class_id', '')::INTEGER;

        INSERT INTO video_corpus (
            video_id, content_type, content_class_id, creator_handle, tiktok_url,
            thumbnail_url, video_url, frame_urls, analysis_json,
            views, likes, comments, shares, engagement_rate,
            indexed_at,
            ingest_source, first_seen_at, last_refreshed_at, quality_tier,
            niche_resolution_source, niche_resolution_confidence, inferred_creator_niche_id,
            ingest_loop_niche_id, ingest_loop_content_class_id,
            class_assignment_tier, class_assignment_disagreement, score_cohort_mismatch,
            boost_attribution, reference_eligible, ingest_relaxation_tier,
            breakout_ratio, creator_median_views, creator_tier,
            content_format, hook_type, language,
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
            COALESCE(r->>'boost_attribution', 'unknown'),
            COALESCE((r->>'reference_eligible')::BOOLEAN, true),
            COALESCE(NULLIF(r->>'ingest_relaxation_tier', '')::SMALLINT, 0),
            NULLIF(r->>'breakout_ratio', '')::NUMERIC,
            NULLIF(r->>'creator_median_views', '')::BIGINT,
            r->>'creator_tier',
            r->>'content_format',
            r->>'hook_type',
            COALESCE(r->>'language', 'vi'),
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
            boost_attribution            = EXCLUDED.boost_attribution,
            reference_eligible           = EXCLUDED.reference_eligible,
            ingest_relaxation_tier       = EXCLUDED.ingest_relaxation_tier,
            breakout_ratio               = COALESCE(EXCLUDED.breakout_ratio, video_corpus.breakout_ratio),
            creator_median_views         = COALESCE(EXCLUDED.creator_median_views, video_corpus.creator_median_views),
            creator_tier                 = COALESCE(EXCLUDED.creator_tier, video_corpus.creator_tier),
            content_format               = COALESCE(EXCLUDED.content_format, video_corpus.content_format),
            hook_type                    = COALESCE(EXCLUDED.hook_type, video_corpus.hook_type),
            language                     = COALESCE(EXCLUDED.language, video_corpus.language),
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
  'Unified batch upsert: class pivot + M1 boost/relax + M4 stats_history + breakout_ratio (20260828000001).';

-- Backfill M4 t0 snapshots for recent batch rows missing stats_history (23/05 partial deploy).
UPDATE video_corpus
SET stats_history = jsonb_build_array(
    jsonb_build_object(
        'at', COALESCE(first_seen_at, indexed_at, now()),
        'phase', 't0',
        'views', views,
        'likes', likes,
        'comments', comments,
        'shares', shares
    )
)
WHERE ingest_source = 'batch_nightly'
  AND jsonb_array_length(COALESCE(stats_history, '[]'::jsonb)) = 0
  AND first_seen_at >= NOW() - INTERVAL '7 days';
