# /phase4

Tech Lead writes the tech spec directly. Runs after the UI reference is available (`artifacts/uiux-reference/` and/or optional `src/make-import/`).

## Pre-flight checks

Before starting, confirm:
- [ ] `artifacts/docs/screen-specs-[app]-v1.md` exists and is approved
- [ ] `artifacts/uiux-reference/` is current (or optional `src/make-import/` exists)
- [ ] `artifacts/docs/northstar-[app].html` exists
- [ ] `artifacts/docs/tech-spec.md` does NOT exist (not already run)

If any check fails: report to human, do not proceed.

## Read first

```
artifacts/docs/northstar-[app].html
artifacts/docs/screen-specs-[app]-v1.md
artifacts/docs/emotional-design-system.md
artifacts/uiux-reference/data.js       ← read mock data shapes to derive schema (optional src/make-import/)
.cursor/skills/tech-spec/SKILL.md      ← full output format and quality checks
```

## Step 1 — Integration Research Check

Scan northstar §10 and §11 for every external service. For each:
- Check if `artifacts/integrations/[integration-name].md` exists

If any integration docs are **missing**: dispatch the Research Agent for each, wait for completion.

## Step 2 — Write the Tech Spec

Follow the tech-spec skill exactly — all sections and quality checks are defined there.

Key architecture notes for this stack:
- §7: SPA data flow — React → Supabase (publishable key + JWT) → Postgres (RLS)
- §9: Data Access Layer = client-side hooks and query functions, not Server Component reads
- §10: Edge Functions replace API routes — most mutations are direct client → RLS
- §12: `VITE_` prefix for client-safe vars, `supabase secrets set` for server-only
- §15: Cron jobs via Supabase Edge Functions + pg_cron, not Vercel Cron
- §18: Pre-rendered landing page, static SEO files, PWA via Vite plugin

Create `supabase/seed.sql` with realistic rows after defining the schema.

## After completion

1. Update `artifacts/plans/project-plan.md` — mark Phase 4 complete
2. Update `agent-workspace/ACTIVE_CONTEXT.md`
3. Present to human: "Tech spec complete. Review `artifacts/docs/tech-spec.md`. Approve to proceed to `/setup`."
4. On approval: commit `docs(phase4): tech spec complete`
