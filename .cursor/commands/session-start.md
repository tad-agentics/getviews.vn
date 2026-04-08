# /session-start

Restore working context and report status to the human.

## Steps

1. Check if `agent-workspace/ACTIVE_CONTEXT.md` exists:
   - **Yes:** read it
   - **No:** copy `artifacts/templates/ACTIVE_CONTEXT.md` to `agent-workspace/ACTIVE_CONTEXT.md`, then report "First session detected — run `/init` to initialize the project before any phase commands."
2. Read yesterday's memory file if present (`agent-workspace/memory/[yesterday].md`) — focus on the `## Session end` block for carry-over items
3. Check if `agent-workspace/memory/[today].md` exists:
   - **No:** copy `artifacts/templates/memory-YYYY-MM-DD.md` to `agent-workspace/memory/[today].md`, then write the `## Session start` block with context restored from ACTIVE_CONTEXT and any carry-over from yesterday's session end
   - **Yes:** session already started — read it and continue from where it left off
4. Read `artifacts/plans/project-plan.md`
5. Run `git log --oneline -10`
6. Check `artifacts/docs/changelog.md` — count open BLOCKING items
7. Check `artifacts/issues/` — count open issues

## Report to human

```
## Session Start — [YYYY-MM-DD]

**Current focus:** [from ACTIVE_CONTEXT]

**Feature workstreams:**
[list each active feature with status: backend / frontend / qa / done]

**Next action:** [exact first thing to do this session]

**Open blockers:** [count + description, or "None"]
**Open issues:** [count, or "None"]
**Changelog blocking items:** [count, or "None"]
```

If ACTIVE_CONTEXT and memory give contradictory pictures, resolve before reporting.
