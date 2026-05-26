-- Persist V5 channel findings for deep diagnosis cache replay (§5.1 gap 3).

ALTER TABLE public.channel_diagnoses
  ADD COLUMN IF NOT EXISTS channel_findings jsonb NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.channel_diagnoses.channel_findings IS
  'Serialized ChannelFinding[] for deep UI tile + cache replay (finding_id, teaser, strength, section_hint).';
