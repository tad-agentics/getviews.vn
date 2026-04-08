# /new-feature [brief description]

Kick off a full new-feature development cycle: gather requirements → propose design → create feature doc → dispatch agents → report result.

Use this for features added after the initial build. Each feature gets its own scoped doc and runs the standard Backend → Frontend → QA pipeline.

Usage: `/new-feature add dark mode toggle` or `/new-feature user notification preferences`

---

## Step 1 — Requirements Gathering

Ask the human these questions (only what isn't already clear from the brief description):

- **What problem does this solve?** One sentence from the user's perspective.
- **Which screens are affected?** New screens, modified screens, or both?
- **Does it touch the database?** New tables, new columns, or read-only?
- **Any new external integrations?** (Stripe, email, LLM, third-party API)
- **Acceptance criteria** — what does "done" look like? List 3–5 testable conditions.

Do not ask questions already answered by the brief description. Synthesize what you know before asking.

---

## Step 2 — Proposal

Present a concise implementation plan for human approval:

```
## Feature Proposal: [Feature Name]

**Problem:** [one sentence]

**Solution:** [what will be built]

**Scope:**
- Backend: [new tables / columns / API routes / none]
- Frontend: [new screens / modified screens / components]
- Integrations: [any new external deps or none]

**Affected files / areas:**
- [list key files or routes that will change]

**Acceptance criteria:**
1. [testable condition]
2. [testable condition]
3. [testable condition]

**Estimated complexity:** [Simple / Medium / Complex]
```

Wait for human approval before proceeding. If the human requests changes, revise and re-present.

---

## Step 3 — Research (if new integrations)

If the proposal includes a new external integration not already in `artifacts/integrations/`:

```
Run /research for: [integration name]
```

Wait for research doc(s) to be written to `artifacts/integrations/` before continuing.

---

## Step 4 — Feature Doc

On approval, create `artifacts/docs/features/[feature-name].md`:

```markdown
# Feature: [Feature Name]

**Status:** in-progress
**Created:** YYYY-MM-DD
**Approved by:** human

---

## Problem
[one sentence]

## Solution
[what is being built]

## Acceptance Criteria
- [ ] [testable condition]
- [ ] [testable condition]
- [ ] [testable condition]

## Backend Scope
[tables, columns, RLS, Edge Functions — or "none"]

## Frontend Scope
[screens, Make component names to copy, interactions — or new screens to build from screen specs]

## Integration Notes
[links to artifacts/integrations/ docs if applicable, or "none"]

## Implementation Notes
[any architectural decisions, constraints, or gotchas]

---

## Progress

| Layer | Status | Commit |
|---|---|---|
| Backend | pending | — |
| Frontend | pending | — |
| QA | pending | — |

## QA Result
[PASS / BLOCKING — filled in after QA]
```

Update `artifacts/plans/project-plan.md` to add this feature to the tracker.

---

## Step 5 — Dispatch

Add this feature to `artifacts/plans/build-plan.md` under a new wave or append to the current wave, with a full context package (backend scope, frontend scope, acceptance criteria).

Then dispatch:

```
/feature [feature-name]
```

The standard Backend → Frontend → QA pipeline runs. Each agent reads the feature doc as part of its context package in `build-plan.md`.

---

## Step 6 — Report + Update

When QA signals PASS or BLOCKING:

**On PASS:**
1. Update `artifacts/docs/features/[feature-name].md` — mark status: complete, fill in QA Result: PASS, add commit hashes to Progress table
2. Update `artifacts/plans/project-plan.md` — mark feature complete
3. Update `agent-workspace/ACTIVE_CONTEXT.md`
4. Report to human: "Feature [name] complete. [brief summary of what shipped]"

**On BLOCKING:**
1. Update feature doc — add BLOCKING issues to QA Result section
2. Open `artifacts/issues/[issue-name].md` for each blocking issue
3. Report to human: "Feature [name] blocked. [list issues]. Dispatching fix."
4. Dispatch relevant agent for fix, then re-run QA step
