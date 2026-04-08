---
name: dogfood
description: Structured dogfooding session — the builder uses the staging app to complete real tasks and records what breaks. Run between /visual-audit and /pre-handoff.
---

# /dogfood — Structured Product Testing

> Run after `/visual-audit` and before `/pre-handoff`. The builder (human) uses the staging app as a real user for 30–60 minutes. This step catches problems that specs and agents cannot anticipate — confusing flows, wrong defaults, missing affordances, awkward copy in context.

## Step 1 — Generate the task list

Read these files to generate a task list the human will execute:

- `artifacts/docs/northstar-[app].html` — §3 (Solution), §7 (Build Scope), §13 (User Scenarios if present)
- `artifacts/plans/build-plan.md` — feature list
- `agent-workspace/temp/office-hours-risks.md` — assumptions to validate (if exists)

Generate a task list covering:

### Core loop tasks (mandatory)
- Complete the core loop end-to-end 3 times with different inputs
- Each run should produce a different result or state

### Edge case tasks (mandatory)
- Use the app on mobile (375px viewport)
- Try to do something the app should prevent (access another user's data, negative credits, etc.)
- Leave a form half-filled and navigate away, then return
- Use the back button at every screen transition
- Trigger every error state you can (disconnect network, submit invalid data)

### Assumption validation tasks (from office-hours risks)
For each assumption in `office-hours-risks.md`, include a task that tests it:

| Assumption | Dogfooding task |
|---|---|
| "Users will pay after seeing partial results" | Complete a free action, then encounter a paywall. Is the partial result compelling enough? |
| "Users understand the credit system" | Check the credit balance display. Is the cost per action clear before committing? |

### Emotional experience tasks
- Is the first-time experience welcoming or confusing?
- After completing the core loop, do you feel the emotion the EDS describes?
- Is there a moment where the app feels slow, even if technically fast?
- Is there any screen where you had to think about what to do next?

### Output format

Present the task list to the human:

```markdown
## Dogfooding Task List — [App Name]

Staging URL: [url]
Time budget: 30–60 minutes
Device: Phone (primary) + Desktop (secondary)

### Core Loop (do 3 times)
1. [specific task with specific inputs]
2. [different inputs]
3. [edge case inputs]

### Edge Cases
4. [mobile test]
5. [auth boundary test]
6. [form abandonment test]
7. [back button test]
8. [error trigger test]

### Assumption Tests
9. [task from office-hours risks]
10. [task from office-hours risks]

### Emotional Check
11. Rate first-time experience: confused / neutral / welcoming / delighted
12. Rate core loop completion feeling: frustrated / neutral / satisfied / excited
13. Name one screen where you hesitated
14. Name one thing you expected but couldn't find
```

## Step 2 — Record findings

After the human completes the task list, collect findings in this format:

```markdown
## Dogfooding Report — [App Name]
**Date:** [date]
**Tester:** [human name]
**Device(s):** [phone model + browser, desktop browser]
**Duration:** [minutes spent]

### Findings

| # | Severity | Screen | Finding | Expected behavior |
|---|---|---|---|---|
| 1 | BLOCKING | [screen] | [what happened] | [what should happen] |
| 2 | SHOULD_FIX | [screen] | [what happened] | [what should happen] |
| 3 | NICE_TO_HAVE | [screen] | [what happened] | [what should happen] |

### Assumption Validation

| Assumption | Result | Action |
|---|---|---|
| [from office-hours] | VALIDATED / INVALIDATED / UNCLEAR | [what to do if invalidated] |

### Emotional Assessment
- First-time experience: [rating + why]
- Core loop feeling: [rating + why]
- Hesitation screen: [screen name + why]
- Missing expectation: [what + why they expected it]

### Overall Verdict
[SHIP / FIX_THEN_SHIP / RETHINK — with reasoning]
```

Save to `artifacts/qa-reports/dogfood-report.md`.

## Step 3 — Triage findings

Categorize findings:

**BLOCKING** — create issues in `artifacts/issues/`, dispatch relevant agent for fix, then re-run `/visual-audit` on affected screens.

**SHOULD_FIX** — create issues, include in pre-handoff scope. QA agent picks these up during `/pre-handoff`.

**NICE_TO_HAVE** — log in `artifacts/docs/changelog.md` as deferred items. Do not fix before deploy.

**INVALIDATED assumptions** — present to human with options:
- A) Accept the current behavior (update the northstar to match reality)
- B) Fix the behavior (dispatch relevant agent)
- C) Defer to post-launch (add to changelog)

## Step 4 — Gate

**If 0 BLOCKING findings:** Proceed to `/pre-handoff`.

**If BLOCKING findings exist:** Fix all, re-verify affected screens, then proceed to `/pre-handoff`.

```
Dogfooding complete.
Findings: [N] blocking / [M] should-fix / [K] nice-to-have
Assumptions: [X] validated / [Y] invalidated / [Z] unclear

[If clean:] Ready for pre-handoff. Run /pre-handoff.
[If blocking:] [N] blocking items need fixing before pre-handoff. Issues created in artifacts/issues/.
```
