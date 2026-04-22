-- Phase 4: Move pg_trgm and pg_net from public schema to extensions schema.
--
-- Extensions in the public schema expose their functions and operators to
-- anon/authenticated roles via PostgREST, increasing the attack surface.
-- The extensions schema is not exposed by PostgREST by default.
--
-- pg_trgm backs 3 GIN indexes for history search (search_sessions RPC).
-- Moving the extension requires dropping and recreating those indexes
-- because the operator class name is schema-qualified in the index definition.
-- The window where those indexes are absent is ~1-2 seconds; the planner
-- falls back to seq scan on chat_messages (54 rows) and answer_sessions (2 rows)
-- during that window — imperceptible.
--
-- pg_net is used only by Supabase internals and pg_cron Edge Function calls;
-- it does not back any user-facing indexes, so its move is instant.

-- ── pg_trgm ───────────────────────────────────────────────────────────────────

-- Step 1: Drop the 3 GIN indexes that reference gin_trgm_ops by unqualified name.
drop index if exists public.idx_chat_messages_content_trgm;
drop index if exists public.idx_answer_sessions_title_trgm;
drop index if exists public.idx_answer_sessions_initial_q_trgm;

-- Step 2: Move pg_trgm to the extensions schema.
alter extension pg_trgm set schema extensions;

-- Step 3: Recreate the 3 GIN indexes with the fully-qualified operator class.
create index idx_chat_messages_content_trgm
  on public.chat_messages using gin (content extensions.gin_trgm_ops);

create index idx_answer_sessions_title_trgm
  on public.answer_sessions using gin (title extensions.gin_trgm_ops);

create index idx_answer_sessions_initial_q_trgm
  on public.answer_sessions using gin (initial_q extensions.gin_trgm_ops);

-- ── pg_net ────────────────────────────────────────────────────────────────────
-- pg_net does NOT support ALTER EXTENSION ... SET SCHEMA (SQLSTATE 0A000).
-- It is a C extension that hard-codes schema references internally.
-- Leaving it in public schema; no user-facing functions or indexes are exposed
-- through it, so the attack-surface impact is minimal compared to pg_trgm.
