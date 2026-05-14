-- Migration: channel_diagnoses table
-- Stores Lightreel-style narrative channel diagnoses keyed by (handle, video_url, niche_id).
-- Writes are service_role-only (RLS blocks client writes).
-- Do NOT touch channel_formulas — that is Phase 2 cleanup.

CREATE TABLE IF NOT EXISTS public.channel_diagnoses (
    handle              text        NOT NULL,
    video_url           text        NOT NULL DEFAULT '',
    niche_id            integer     NOT NULL,
    trajectory_shape    text        NOT NULL,
    sections            jsonb       NOT NULL DEFAULT '[]',
    recommendations     jsonb       NOT NULL DEFAULT '[]',
    top_performers      jsonb       NOT NULL DEFAULT '[]',
    worst_performers    jsonb       NOT NULL DEFAULT '[]',
    ugc_creators        jsonb       NOT NULL DEFAULT '[]',
    channel_pattern     jsonb       NOT NULL DEFAULT '{}',
    inflection          jsonb,
    creator_match       jsonb,
    video_count         integer     NOT NULL DEFAULT 0,
    computed_at         timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (handle, video_url, niche_id)
);

COMMENT ON TABLE public.channel_diagnoses IS
    'Lightreel-style narrative channel diagnoses. PK=(handle, video_url, niche_id). '
    'Service-role writes only. 7-day TTL enforced by application layer.';

COMMENT ON COLUMN public.channel_diagnoses.video_url IS
    'Empty string when no target video was supplied. Part of PK to allow '
    'per-video vs channel-only caches to coexist.';

COMMENT ON COLUMN public.channel_diagnoses.trajectory_shape IS
    'One of: decline_from_peak | stagnant | steady_growth | breakout | bursty | new_account';

COMMENT ON COLUMN public.channel_diagnoses.sections IS
    'Array of {section_id, title, text} objects in narrative display order.';

COMMENT ON COLUMN public.channel_diagnoses.recommendations IS
    'Array of {index, title, body} objects (numbered 1-7).';

COMMENT ON COLUMN public.channel_diagnoses.top_performers IS
    'Array of PerformerTile objects (thumbnail_url, video_url, views, format, caption_snippet).';

COMMENT ON COLUMN public.channel_diagnoses.worst_performers IS
    'Array of PerformerTile objects for under-performing videos.';

COMMENT ON COLUMN public.channel_diagnoses.ugc_creators IS
    'Array of UGCCreator objects scouted for competitive landscape section.';

COMMENT ON COLUMN public.channel_diagnoses.channel_pattern IS
    'Output of build_channel_pattern(): global_avg_views, total_videos, formats map.';

COMMENT ON COLUMN public.channel_diagnoses.inflection IS
    'Output of compute_inflection_point() or null if no inflection found.';

COMMENT ON COLUMN public.channel_diagnoses.creator_match IS
    'Percentile/tier of the target video vs channel baseline, or null.';

-- Index for cache lookups: recent rows per handle+niche (covers 7-day TTL scan).
CREATE INDEX IF NOT EXISTS channel_diagnoses_handle_niche_computed_at_idx
    ON public.channel_diagnoses (handle, niche_id, computed_at DESC);

-- Enable RLS
ALTER TABLE public.channel_diagnoses ENABLE ROW LEVEL SECURITY;

-- Policy: service_role can read/write everything (bypasses RLS by default in Supabase).
-- Authenticated users may only read their own queries — but since this table has no
-- user_id FK (shared public cache by handle), we expose read-only via a restricted policy.
-- Writes are only via service_role (Cloud Run).

CREATE POLICY "allow_authenticated_read_channel_diagnoses"
    ON public.channel_diagnoses
    FOR SELECT
    TO authenticated
    USING (true);

-- No INSERT/UPDATE/DELETE policies for authenticated role — service_role only.
