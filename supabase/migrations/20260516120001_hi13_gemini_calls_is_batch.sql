-- HI-13 — Attribute Gemini Batch API extractions in gemini_calls (50% pricing tier).
ALTER TABLE public.gemini_calls
  ADD COLUMN IF NOT EXISTS is_batch boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.gemini_calls.is_batch IS
  'True when cost_usd uses batch-tier token rates (Gemini Batch API).';
