-- Extend provenance-safe RPC with HI-11 shadow niche columns (nullable).

CREATE OR REPLACE FUNCTION upsert_video_corpus_batch(
    p_rows JSONB
)
RETURNS TABLE (video_id TEXT, action TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    r JSONB;
    v_video_id TEXT;
    v_action TEXT;
BEGIN
    FOR r IN SELECT * FROM jsonb_array_elements(p_rows)
    LOOP
        v_video_id := r->>'video_id';

        INSERT INTO video_corpus (
            video_id, content_type, niche_id, creator_handle, tiktok_url,
            thumbnail_url, video_url, frame_urls, analysis_json,
            views, likes, comments, shares, engagement_rate,
            indexed_at,
            ingest_source, first_seen_at, last_refreshed_at, quality_tier,
            niche_resolution_source, niche_resolution_confidence, inferred_creator_niche_id
        )
        VALUES (
            v_video_id,
            COALESCE(r->>'content_type', 'video'),
            (r->>'niche_id')::INTEGER,
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
            NULLIF(r->>'inferred_creator_niche_id', '')::INTEGER
        )
        ON CONFLICT (video_id) DO UPDATE SET
            content_type        = EXCLUDED.content_type,
            niche_id            = EXCLUDED.niche_id,
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
            inferred_creator_niche_id    = EXCLUDED.inferred_creator_niche_id
        RETURNING video_corpus.video_id, 'upserted';

        video_id := v_video_id;
        action   := 'upserted';
        RETURN NEXT;
    END LOOP;
END;
$$;

GRANT EXECUTE ON FUNCTION upsert_video_corpus_batch(JSONB) TO service_role;
