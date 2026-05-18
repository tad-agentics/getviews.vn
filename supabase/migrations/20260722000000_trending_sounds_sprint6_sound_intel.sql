-- Sprint 6 (diagnosis-first §6): Layer 0B sound intelligence columns for trending_sounds.
-- Populated by sound_aggregation; optional dialect_audio for future enrichment.

ALTER TABLE public.trending_sounds
  ADD COLUMN IF NOT EXISTS lifecycle_phase TEXT,
  ADD COLUMN IF NOT EXISTS commercial_music_library_eligible BOOLEAN,
  ADD COLUMN IF NOT EXISTS dialect_audio TEXT;

COMMENT ON COLUMN public.trending_sounds.lifecycle_phase IS
  'emerging|growth|peak|parody|decline — heuristic from week-over-week usage; NULL if unknown';
COMMENT ON COLUMN public.trending_sounds.commercial_music_library_eligible IS
  'TikTok CML eligibility when known; NULL = unknown (signals skip strict CML warnings)';
COMMENT ON COLUMN public.trending_sounds.dialect_audio IS
  'Regional flavour detected in BGM/vocal mix (optional; often NULL)';
