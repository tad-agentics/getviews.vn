-- Round B (2026-05-19): class-first trends sounds + drop legacy niche_intelligence MV.
-- ``video_corpus.niche_id`` column retained for thin-junction fallback reads until Phase C.

-- ── trending_sounds: pivot key from niche_id → content_class_id ─────────────
ALTER TABLE public.trending_sounds
  ADD COLUMN IF NOT EXISTS content_class_id INT REFERENCES public.content_classifications(id) ON DELETE CASCADE;

-- Stale niche-keyed rows are incompatible with the class aggregator; batch repopulates.
TRUNCATE public.trending_sounds;

DROP INDEX IF EXISTS public.idx_trending_sounds_niche_sound_week;

ALTER TABLE public.trending_sounds
  DROP COLUMN IF EXISTS niche_id;

CREATE UNIQUE INDEX IF NOT EXISTS idx_trending_sounds_class_sound_week
  ON public.trending_sounds(content_class_id, sound_id, week_of);

CREATE INDEX IF NOT EXISTS idx_trending_sounds_content_class_week
  ON public.trending_sounds(content_class_id, week_of DESC);

COMMENT ON COLUMN public.trending_sounds.content_class_id IS
  'Round B — weekly sound aggregate scoped to content_class (replaces niche_id).';

-- ── Drop legacy niche_intelligence MV + refresh RPC ───────────────────────────
DROP MATERIALIZED VIEW IF EXISTS public.niche_intelligence CASCADE;

DROP FUNCTION IF EXISTS public.refresh_niche_intelligence();

-- Live benchmark thin fallback uses content_class_intelligence + tier MV only;
-- niche MV consumers on SPA migrated in Round B (ExploreScreen, useTopNiches).
