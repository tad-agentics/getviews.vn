-- Drop credit_transactions.session_id (audit 2026-06-10 M-5, executed per
-- destructive-migration checklist).
--
-- The column referenced chat_sessions, which Phase C dropped with CASCADE
-- (20260830000001) — the FK vanished silently and the column has pointed at
-- nothing since. Checklist greps confirmed zero readers/writers across all
-- three runtimes and all SQL function bodies (the only ledger writers are
-- decrement_and_grant_credits / grant path and refund_credit, neither
-- touches session_id). Historical values reference deleted rows and carry
-- no recoverable meaning.

ALTER TABLE public.credit_transactions DROP COLUMN IF EXISTS session_id;
