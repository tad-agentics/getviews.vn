# Destructive migration checklist

Written after the Phase C `video_corpus.niche_id` drop left three undetected
casualties (audit 2026-06-10): a live 400 in `api/landing-stats.ts`, a
silently-CASCADE'd FK on `credit_transactions.session_id`, and stale
CLAUDE.md. The migration itself was careful — the blast-radius check wasn't.
Run this list for every migration that DROPs/RENAMEs a table or column, or
changes a function signature.

## Before writing the migration

1. **Grep all three runtimes + docs** for the identifier being dropped:
   ```bash
   grep -rn "<column_or_table>" src/ shared/ api/ cloud-run/getviews_pipeline/ \
     supabase/functions/ CLAUDE.md artifacts/docs/system-design.md
   ```
   Every hit is either (a) migrated in the same PR, (b) explicitly listed in
   the migration header as intentionally-left (with a removal date), or
   (c) a blocker.
2. **Check FK in-edges** — `DROP TABLE ... CASCADE` deletes constraints on
   *other* tables without a trace:
   ```sql
   SELECT conrelid::regclass AS referencing_table, conname
   FROM pg_constraint WHERE confrelid = '<table>'::regclass;
   ```
   Decide per-FK: re-point, drop column, or keep orphaned (document why).
3. **Check DB-side consumers** the greps can't see: views/MVs
   (`pg_depend`), RPC bodies (`SELECT proname FROM pg_proc WHERE prosrc
   ILIKE '%<identifier>%'`), pg_cron command strings, and
   `expected_cron_jobs` if a job is retired.
4. **Check PostgREST shape**: any FE/Edge `.select("...")` string listing the
   column fails at runtime with a 400, not at typecheck — grep for the
   column name inside quotes in `.select(` calls specifically.

## In the same commit

5. Regenerate `src/lib/database.types.ts`.
6. Update `system-design.md` and CLAUDE.md if they name the object.
7. Apply via Supabase MCP **and** commit the identical local SQL file.

## After applying

8. Smoke the surfaces that touched the identifier (the Phase C miss was the
   *unauthenticated landing page* — don't only test logged-in flows).
9. `SELECT * FROM admin_cron_inventory_drift();` if any cron was touched.
