-- Phase D.5.4 — 90-day chat_sessions archival audit table.
--
-- The `cron-chat-archival` Edge Function runs nightly and hard-deletes any
-- chat_sessions row with updated_at < now() - 90 days (cascade removes the
-- owning chat_messages rows per the existing FK). Before the delete, one
-- row lands here so the deletion history is queryable for support + data
-- retention compliance.
--
-- This is an audit table: service_role writes only, no authenticated grants.
-- The cron function derives message_count at archive time from
-- `count(chat_messages)` rather than a column on chat_sessions to avoid
-- drift with the live row count — even if a past migration neglects to
-- maintain a denormalised counter, the audit stays honest.

CREATE TABLE IF NOT EXISTS public.chat_archival_audit (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     UUID NOT NULL,
  user_id        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  message_count  INTEGER NOT NULL,
  session_created_at  TIMESTAMPTZ,
  session_updated_at  TIMESTAMPTZ,
  archived_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT chat_archival_audit_message_count_nonneg CHECK (message_count >= 0)
);

-- Dashboard query pattern: "what did we delete yesterday?" — archived_at
-- desc. Partial index isn't needed; the table is small (N deletions per
-- night) and never grows faster than chat_sessions shrinks.
CREATE INDEX IF NOT EXISTS chat_archival_audit_archived_at_idx
  ON public.chat_archival_audit (archived_at DESC);

-- Per-user lookup for support tickets ("where did my chat from March go?").
CREATE INDEX IF NOT EXISTS chat_archival_audit_user_id_idx
  ON public.chat_archival_audit (user_id, archived_at DESC)
  WHERE user_id IS NOT NULL;

COMMENT ON TABLE public.chat_archival_audit IS
  'Phase D.5.4: one row inserted per chat_sessions hard-delete by the '
  'cron-chat-archival Edge Function (nightly at 03:00 UTC). Cascade drops '
  'chat_messages per existing FK; this audit captures the delete before it '
  'happens so support can answer "what happened to my chat from 100 days '
  'ago". service_role writes only; authenticated has no grants.';

COMMENT ON COLUMN public.chat_archival_audit.message_count IS
  'Snapshot of count(chat_messages WHERE session_id = ...) at archive time. '
  'Used for capacity planning (average session size).';

ALTER TABLE public.chat_archival_audit ENABLE ROW LEVEL SECURITY;

-- No policies. service_role bypasses RLS; authenticated has no grants,
-- no SELECT / INSERT / UPDATE / DELETE paths exposed to the client.
