-- Defensive backfill trigger for ``video_corpus.content_class_id``.
--
-- Background: between 2026-05-05 and 2026-05-07, ~730 rows landed with
-- ``content_class_id = NULL`` despite ``corpus_ingest.py:1269`` calling
-- ``_content_class_for(niche_id, content_format)`` and including the
-- result in the upsert payload. Root cause was never confirmed (likely
-- env-var-wipe cascade silently breaking the Python helper for some
-- ingest passes), but the symptom was real: 14% of corpus stuck with
-- NULL ``content_class_id``, breaking pattern thesis sample selection
-- and ``hook_effectiveness`` grouping.
--
-- This trigger guarantees the column is never NULL on a row whose
-- ``niche_id`` is set. If the application-side helper succeeded, the
-- value already matches what the trigger would compute, so the trigger
-- is a no-op (no write amplification). If the helper failed/returned
-- NULL, the trigger fills it from ``map_legacy_corpus_to_content_class``
-- so the failure self-heals at write time.
--
-- Idempotent: ``CREATE OR REPLACE`` for the function, ``DROP TRIGGER IF
-- EXISTS`` then ``CREATE TRIGGER`` for the trigger.

CREATE OR REPLACE FUNCTION video_corpus_fill_content_class_id()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.content_class_id IS NULL AND NEW.niche_id IS NOT NULL THEN
    NEW.content_class_id := map_legacy_corpus_to_content_class(
      NEW.niche_id, NEW.content_format
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_video_corpus_fill_content_class_id ON public.video_corpus;

CREATE TRIGGER trg_video_corpus_fill_content_class_id
  BEFORE INSERT OR UPDATE OF niche_id, content_format ON public.video_corpus
  FOR EACH ROW
  EXECUTE FUNCTION video_corpus_fill_content_class_id();

COMMENT ON FUNCTION video_corpus_fill_content_class_id IS
  'Defensive auto-fill so rows whose application-side _content_class_for() helper failed or returned NULL still get a valid content_class_id at write time. No-op when the value is already set.';
