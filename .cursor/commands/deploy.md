# /deploy [production-supabase-ref]

Dispatch the DevOps Agent for production deploy.
Runs after the pre-handoff gate is approved.

**Input required:** The human must provide the production Supabase project ref. If not provided, ask for it before proceeding.

## Pre-flight checks

Before dispatching, confirm:
- [ ] All features in `artifacts/plans/project-plan.md` are marked complete
- [ ] Visual fidelity audit complete (Product Designer)
- [ ] Pre-handoff review complete (`test: pre-handoff review complete` commit present)
- [ ] `artifacts/docs/changelog.md` — 0 BLOCKING items
- [ ] `artifacts/issues/` — 0 open BLOCKING issues
- [ ] Human has explicitly said "approved" on the pre-handoff gate

If any check fails: report to human, do not dispatch.

## Dispatch

Launch DevOps Agent subagent (foreground):

```
Task: Production Deploy

Production Supabase project ref: [PRODUCTION_REF from human input]

Read:
- .cursor/agents/devops-agent.md (your full instructions)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/tech-spec.md
- artifacts/docs/changelog.md

Follow the deploy process in your agent file exactly.
Use the production Supabase ref above for `supabase link --project-ref`.
Confirm at each step before proceeding to the next.
Signal completion with production URL confirmed live.
```

## After completion

1. Update `artifacts/plans/project-plan.md` — mark deploy complete
2. Update `agent-workspace/ACTIVE_CONTEXT.md` — project shipped
3. Report to human: "Production deploy complete. URL: [url]. Smoke check passed."
