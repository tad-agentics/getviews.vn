---
name: investigate
description: Systematic debugging with root cause investigation. Iron Law — no fixes without root cause. Dispatched by the Tech Lead when BLOCKING items are complex or when fixes touch >3 files.
disable-model-invocation: true
---

# Investigate — Root Cause Analysis

**Iron Law: No code changes until root cause is identified.**

This skill is for complex bugs where the fix is not obvious. If you can see the fix in under 2 minutes, skip this skill and fix directly. Use this when: the bug spans multiple files, the cause is unclear, or a previous fix attempt was reverted.

## Phase 1: Investigate

Gather evidence. Do not hypothesize yet.

1. **Reproduce** — confirm the bug exists. Get the exact steps to trigger it.
2. **Isolate** — narrow the scope. Which files, which functions, which data state?
3. **Trace** — follow the data flow from input to output. Where does the expected path diverge from actual?
4. **Log** — check console errors, Supabase logs, network responses. Capture exact error messages.

```bash
# Check recent changes that may have introduced the bug
git log --oneline -20 --all -- [suspected-files]
git diff HEAD~5 -- [suspected-files]
```

Write findings to `agent-workspace/temp/investigate-[issue].md`:

```markdown
## Evidence
- Reproduction steps: [exact steps]
- Error output: [exact message]
- Affected files: [list]
- Data state at failure: [what the data looks like when it breaks]
```

## Phase 2: Analyze

Review the evidence. Identify patterns.

- What changed recently in the affected files?
- Does this bug occur in all states or only specific data conditions?
- Is this a regression (worked before, broke after a specific commit)?
- Is the bug in frontend logic, backend logic, RLS policy, or data schema?

## Phase 3: Hypothesize

Formulate exactly one hypothesis. State it as a falsifiable claim:

```markdown
## Hypothesis
"The bug occurs because [X] causes [Y] when [Z condition is true]."

## Evidence supporting this:
- [evidence 1]
- [evidence 2]

## How to verify:
- [verification step — if this is true, then ...]
```

**Verify the hypothesis before proceeding.** If the verification fails, return to Phase 1 with new evidence and form a new hypothesis.

## Phase 4: Implement

Only after root cause is confirmed:

1. **Minimal fix** — smallest change that resolves the root cause. Do not refactor.
2. **Single commit** — `fix: [feature]-ISSUE-NNN — [root cause description]`
3. **Verify** — confirm the bug no longer reproduces
4. **Check for regressions** — run `npm run build`, check adjacent functionality
5. **Clean up** — delete `agent-workspace/temp/investigate-[issue].md`

## Scope boundary

During investigation, **only read files** — no edits until Phase 4. If you discover unrelated bugs during investigation, note them in the investigation file but do not fix them. One bug per investigation.

## Escalation

If after 3 investigation cycles (Phase 1 → 3) you cannot identify the root cause:

```
STATUS: BLOCKED
REASON: Root cause not identified after 3 investigation cycles
ATTEMPTED: [summary of hypotheses tested]
RECOMMENDATION: [what the Tech Lead / human should check — e.g. "may require Supabase dashboard inspection" or "likely a race condition that needs production logs"]
```
