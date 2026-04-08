# /phase2

Dispatch the Product Designer to produce screen specs and Figma Make brief.

## Pre-flight checks

Before dispatching, confirm:
- [ ] `artifacts/docs/northstar-[app].html` exists
- [ ] `artifacts/docs/emotional-design-system.md` exists
- [ ] `artifacts/docs/screen-specs-[app]-v1.md` does NOT exist (not already run)

If any check fails: report to human, do not dispatch.

## Dispatch

Launch Product Designer subagent with:

```
Task: Phase 2 — Screen Specs + Figma Make Brief

Read:
- .cursor/agents/product-designer.md (your identity and domain)
- .cursor/skills/wireframes/SKILL.md (your full Phase 2 instructions)
- .cursor/rules/copy-rules.mdc (copy formula, screen-context rules, forbidden words — all copy must be production-ready)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/northstar-[app].html
- artifacts/docs/emotional-design-system.md

Produce:
1. artifacts/docs/screen-specs-[app]-v1.md — screen metadata for every screen
2. artifacts/docs/figma-make-brief.md — structured input for human to use in Figma Make

Follow the Phase 2 skill instructions exactly.
Signal completion by confirming both files are written.
```

## After completion

1. Update `agent-workspace/ACTIVE_CONTEXT.md`
2. Present to human: "Screen specs + Figma Make brief complete. Next steps: (1) Use the Figma Make brief to generate visual designs in Figma Make. (2) Copy all code from Make's Code tab into `src/make-import/`. (3) Approve to proceed to Phase 4."
3. Wait for human to complete Figma Make designs, copy code to `src/make-import/`, AND approve before dispatching `/phase4`
4. On approval: commit `docs(phase2): screen specs + figma make brief complete`
