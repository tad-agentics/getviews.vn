-- Clear stale ``frame_urls`` after thumbnail backfill nulled phantom R2 rows.
--
-- Symptom (2026-05-25 HEAD audit): 2,172 rows with ``thumbnail_url IS NULL`` still
-- had ``frame_urls`` pointing at ``frames/{id}/0.png``, but R2 HEAD returned 404 for
-- 146/146 sampled IDs (zero live objects under frames/ or thumbnails/).
--
-- Idempotent: only rows with no permanent thumbnail and non-empty frame_urls.

BEGIN;

UPDATE public.video_corpus
SET frame_urls = '{}'::text[]
WHERE thumbnail_url IS NULL
  AND frame_urls IS NOT NULL
  AND cardinality(frame_urls) > 0;

COMMIT;
