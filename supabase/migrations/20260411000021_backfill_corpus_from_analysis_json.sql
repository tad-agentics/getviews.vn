-- Backfill Group A columns from existing analysis_json for rows already in corpus.
-- Group B (content_format, cta_type, is_commerce, dialect) and Group D (topics, transcript_snippet)
-- require TypeScript classifiers — run scripts/backfill-corpus-classifiers.ts after this.
-- Group C (ED metadata) CANNOT be backfilled — original API responses were not stored.

UPDATE video_corpus SET
  hook_type         = analysis_json->'hook_analysis'->>'hook_type',
  hook_phrase       = analysis_json->'hook_analysis'->>'hook_phrase',
  face_appears_at   = (NULLIF(analysis_json->'hook_analysis'->>'face_appears_at', ''))::REAL,
  first_frame_type  = COALESCE(analysis_json->'hook_analysis'->>'first_frame_type', 'other'),
  transitions_per_second = (NULLIF(analysis_json->>'transitions_per_second', ''))::REAL,
  tone              = analysis_json->>'tone',
  text_overlay_count = jsonb_array_length(COALESCE(analysis_json->'text_overlays', '[]'::jsonb)),
  scene_count       = jsonb_array_length(COALESCE(analysis_json->'scenes', '[]'::jsonb)),
  video_duration    = (NULLIF(analysis_json->'scenes'->-1->>'end', ''))::REAL,
  language          = 'vi'
WHERE analysis_json IS NOT NULL
  AND analysis_json != '{}'::jsonb;
