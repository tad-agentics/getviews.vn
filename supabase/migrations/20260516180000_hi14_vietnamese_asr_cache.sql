-- HI-14 — Vietnamese supplemental ASR cache + gemini_calls STT attribution.
--
-- Cloud Run calls GCP Speech-to-Text (vi-VN) before Gemini video extraction;
-- results are keyed by TikTok aweme_id (video_id). service_role only (no RLS
-- policies — same pattern as gemini_calls).

CREATE TABLE IF NOT EXISTS public.vietnamese_asr_cache (
  video_id           TEXT PRIMARY KEY,
  transcript         JSONB        NOT NULL,
  stt_cost_usd       NUMERIC(10, 6) NOT NULL DEFAULT 0,
  audio_duration_sec DOUBLE PRECISION,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS vietnamese_asr_cache_created_at_idx
  ON public.vietnamese_asr_cache (created_at DESC);

COMMENT ON TABLE public.vietnamese_asr_cache IS
  'HI-14: GCP Speech-to-Text vi-VN transcript cache per TikTok video_id; '
  'Populated by cloud-run getviews_pipeline.services.asr_vietnamese; service_role only.';

ALTER TABLE public.vietnamese_asr_cache ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.gemini_calls
  ADD COLUMN IF NOT EXISTS gcp_stt_cost_usd NUMERIC(10, 6);

COMMENT ON COLUMN public.gemini_calls.gcp_stt_cost_usd IS
  'HI-14: Vietnamese STT supplemental cost (USD) for this row when video_extraction '
  'ran a paid STT pass in the same request; NULL when unused or cache hit.';
