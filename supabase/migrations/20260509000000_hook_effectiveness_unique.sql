-- 2026-05-09 — add UNIQUE(niche_id, hook_type) on hook_effectiveness.
--
-- Required for the new ``hook_effectiveness_compute.py`` batch job
-- which upserts one row per (niche, hook_type) via ``on_conflict=
-- "niche_id,hook_type"``. Without this constraint, the PostgREST
-- upsert silently falls back to plain INSERT and every weekly run
-- accumulates duplicate rows.
--
-- The table has been empty in production since creation (verified
-- 2026-04-22 in the state-of-corpus audit, Appendix B Gap 1), so
-- there is no data to deduplicate before applying the constraint —
-- the DDL is guaranteed to succeed.

ALTER TABLE public.hook_effectiveness
  ADD CONSTRAINT hook_effectiveness_niche_hook_unique
  UNIQUE (niche_id, hook_type);
