-- Heal legacy ``video_corpus.content_class_id = NULL`` rows (May 2026 ingest gap).
--
-- Symptom: ~730 rows landed with NULL despite ingest setting ``_content_class_for``
-- in the app payload. ``trg_video_corpus_fill_content_class_id`` (20260630000001)
-- only runs on INSERT / UPDATE of ``niche_id`` or ``content_format`` — it does not
-- sweep existing rows. This migration re-applies the same mapping as PR2:
-- ``map_legacy_corpus_to_content_class(niche_id, content_format)``.
--
-- Idempotent: only touches rows where ``content_class_id IS NULL``.
-- Rows where the map returns NULL (unmapped legacy niche × format) stay NULL.

BEGIN;

UPDATE public.video_corpus
SET content_class_id = map_legacy_corpus_to_content_class(niche_id, content_format)
WHERE content_class_id IS NULL
  AND niche_id IS NOT NULL;

COMMIT;
