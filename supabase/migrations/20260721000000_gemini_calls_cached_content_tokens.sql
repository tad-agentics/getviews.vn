-- HI-8 — Record Gemini context-cache hit size on gemini_calls for metering and dashboards.
--
-- ``cached_content_token_count`` mirrors ``usage_metadata.cached_content_token_count``
-- (or Batch JSONL ``usageMetadata.cachedContentTokenCount``). Nullable for legacy rows.
-- ``cost_usd`` is computed in Python with a reduced rate on cached prompt tokens.

ALTER TABLE public.gemini_calls
  ADD COLUMN IF NOT EXISTS cached_content_token_count INTEGER;

COMMENT ON COLUMN public.gemini_calls.cached_content_token_count IS
  'Prompt tokens billed at context-cache rate; subset of tokens_in when HI-8 explicit cache is used.';

ALTER TABLE public.gemini_calls
  DROP CONSTRAINT IF EXISTS gemini_calls_cached_content_nonneg;

ALTER TABLE public.gemini_calls
  ADD CONSTRAINT gemini_calls_cached_content_nonneg
  CHECK (
    cached_content_token_count IS NULL
    OR cached_content_token_count >= 0
  );
