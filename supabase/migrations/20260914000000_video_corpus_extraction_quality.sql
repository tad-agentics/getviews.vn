-- Corpus quality: persist extraction degradation for peer pool + MV structural aggregates.

ALTER TABLE video_corpus
  ADD COLUMN IF NOT EXISTS extraction_quality text NOT NULL DEFAULT 'ok';

COMMENT ON COLUMN video_corpus.extraction_quality IS
  'ok | degraded_scenes | degraded — Gemini extraction quality (TD-7 parity batch + live)';

-- Backfill degraded rows from analysis_json heuristics (parity with classify_extraction_quality).
-- jsonb_typeof / regex guards keep a single malformed row from aborting the migration.
UPDATE video_corpus vc
SET extraction_quality = 'degraded_scenes'
WHERE vc.extraction_quality = 'ok'
  AND vc.content_type = 'video'
  AND jsonb_typeof(vc.analysis_json->'scenes') = 'array'
  AND jsonb_array_length(vc.analysis_json->'scenes') <= 1
  AND (vc.analysis_json->'scenes'->-1->>'end') ~ '^[0-9]+(\.[0-9]+)?$'
  AND (vc.analysis_json->'scenes'->-1->>'end')::double precision > 10;

UPDATE video_corpus vc
SET extraction_quality = 'degraded'
WHERE vc.extraction_quality = 'ok'
  AND vc.content_type = 'video'
  AND jsonb_typeof(vc.analysis_json->'scenes') = 'array'
  AND jsonb_array_length(vc.analysis_json->'scenes') > 1
  AND COALESCE((vc.analysis_json->>'transitions_per_second'), '0') ~ '^[0-9]+(\.[0-9]+)?$'
  AND COALESCE((vc.analysis_json->>'transitions_per_second')::double precision, 0) = 0;
