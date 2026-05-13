-- Phase 6.2 — Protect user_diagnosis provenance when batch upserts the same row.
--
-- Problem: _upsert_rows_sync in corpus_ingest.py uses supabase.table('video_corpus')
-- .upsert(rows, on_conflict='video_id').execute() which generates:
--   ON CONFLICT (video_id) DO UPDATE SET ingest_source = EXCLUDED.ingest_source
-- This would overwrite ingest_source='user_diagnosis' with 'batch_nightly' when
-- the nightly batch indexes a URL a user already diagnosed.
--
-- Fix: create a Postgres RPC function that wraps the upsert with COALESCE so
-- the original ingest_source is preserved, and batch callers switch to this RPC.
--
-- Note: existing_video_ids pre-filter (Phase 6.3) will often prevent batch from
-- even trying to upsert rows that are in the corpus. This RPC is a belt-and-
-- suspenders guard for when that pre-filter misses due to the global vs per-niche
-- dedup leak (fixed in Phase 6.3).

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
            ingest_source, first_seen_at, last_refreshed_at, quality_tier
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
            COALESCE(r->>'quality_tier', 'high')
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
            -- COALESCE: never overwrite user_diagnosis provenance with batch_nightly.
            ingest_source       = COALESCE(video_corpus.ingest_source, EXCLUDED.ingest_source),
            first_seen_at       = COALESCE(video_corpus.first_seen_at, EXCLUDED.first_seen_at),
            last_refreshed_at   = now(),
            quality_tier        = COALESCE(video_corpus.quality_tier, EXCLUDED.quality_tier)
        RETURNING video_corpus.video_id, 'upserted';

        video_id := v_video_id;
        action   := 'upserted';
        RETURN NEXT;
    END LOOP;
END;
$$;

-- Grant execution to service_role (batch only — no anon/authenticated access).
GRANT EXECUTE ON FUNCTION upsert_video_corpus_batch(JSONB) TO service_role;
