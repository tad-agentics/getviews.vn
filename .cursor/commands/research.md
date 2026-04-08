# /research [integration(s)]

Research one or more external integrations and produce structured docs in `artifacts/integrations/`.

Run this before `/phase4` when the northstar includes integrations not yet documented, or before `/new-feature` when a new integration is required.

Usage:
- `/research stripe` — research a single integration
- `/research stripe openai resend` — research multiple integrations in parallel
- `/research` (no args) — scan northstar for all integrations and research all undocumented ones

---

## Pre-flight

1. Read `artifacts/docs/northstar-[app].html` to identify all external integrations
2. Check `artifacts/integrations/` for existing docs
3. Determine which integrations need new or updated docs

If all integrations are already documented and recent (within 30 days): report to human and skip.

---

## Dispatch

For each integration that needs research, launch a Research Agent subagent (run in parallel if multiple):

```
Task: Research integration — [Integration Name]

Read:
- .cursor/agents/research-agent.md (your full instructions)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/northstar-[app].html (what this app specifically needs from this integration)

Research [Integration Name] and produce:
- artifacts/integrations/[integration-name].md

Use Context7 first, then web_search/web_fetch for gaps.
Focus only on what this app needs — not a general overview.
Signal completion by confirming the file is written.
```

---

## After Completion

1. List all docs written to `artifacts/integrations/`
2. Update `agent-workspace/ACTIVE_CONTEXT.md`
3. Report to human:

```
## Research Complete

Integrations documented:
- artifacts/integrations/[name].md — [one line summary of key finding]
- artifacts/integrations/[name].md — [one line summary]

Ready for /phase4 (or /new-feature if that triggered this).
```
