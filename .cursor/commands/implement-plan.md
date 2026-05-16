# /implement-plan [path-to-plan]

Execute a `.cursor/plans/*.plan.md` file one task at a time, with mandatory QA after each.
Each task = dev work + QA pass + atomic commit + changelog append. Move to the next only after all four land.

Usage: `/implement-plan .cursor/plans/pipeline_audit_remediation_plan_(revised_—_quality-first)_d9b0bb76.plan.md`

The discipline rules live in `.cursor/rules/qa-gated-implementation.mdc` (auto-injected). This command adds the explicit dispatch sequence.

## Pre-flight (do all of these in parallel before any code touches keyboard)

1. Read the canonical plan file in full (frontmatter + body)
2. Read `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/qa-gated-implementation.mdc`, `.cursor/rules/project.mdc`
3. Read `agent-workspace/ACTIVE_CONTEXT.md` + latest 1-2 daily memory logs
4. Confirm there are no other in-progress plans (one plan at a time per workspace)
5. Confirm `npm run typecheck` and `pytest` (where applicable) pass on current `main`
6. List the plan's todos via TodoWrite, all `pending`

If any pre-flight check fails, report to human and stop.

## Step 1 — Warm-up (force internalization)

Create `artifacts/issues/<task-id>.md` for every CR/HI/ME/EXP/research/DOC item in the plan, using the template at the bottom of the plan's "Tracking" section.

This is mandatory — it forces you to read every task's body before any code runs.

Commit: `chore(<area>): scaffold issue tracking for <plan-name>`

## Step 2 — Task loop (repeat until all todos complete)

For each pending todo in the order defined by the plan's Sequencing Gantt:

### 2a. Mark in_progress
Update TodoWrite + `agent-workspace/ACTIVE_CONTEXT.md`.

### 2b. Implement
Per the rule's "Per-task workflow" section. Honor dependency graph + calendar waits + conditional outcomes per the rule's contract.

### 2c. Self-check
Confirm acceptance criteria met. Run linter / typecheck / tests. No unrelated changes mixed in.

### 2d. Dispatch QA
Launch `qa-agent` subagent (foreground, blocking) per the rule's QA dispatch template.

### 2e. Act on verdict
Per the rule's step 7. PASS → 2f. PASS_WITH_CONCERNS → judgment call (low-risk: accept + document; high-risk: ask). FAIL → loop 2b. 3 fails → escalate.

### 2f. Commit + changelog
Single commit: code + tests + `artifacts/docs/changelog.md` entry + `artifacts/qa-reports/<task-id>-baseline.json`.

### 2g. Update memory + advance
TodoWrite mark complete. Update ACTIVE_CONTEXT (pop current, push next). Append memory log block.

### 2h. Sprint boundary checkpoint
After the **last executable task listed under each `section …` block** in the plan’s **Sequencing** Mermaid Gantt (not the cross-cutting **Docs** section), pause for human review. Write a clear “Sprint N complete — please review before I proceed to Sprint N+1” message and stop the loop.

**Aligned with the pipeline audit remediation Gantt** (canonical plan under `.cursor/plans/`): **Sprint 1** ends after **CR-4**; **Sprint 2** ends after **EXP-1** (last row in `section Sprint 2 HIGH`); **Sprint 3** ends after **EXP-2** (last row in `section Sprint 3 MEDIUM`). **DOC-1** checkpoints live in **`section Docs (cross-cutting)`** with their own dependencies (`doc1a` after CR-4, `doc1b` after HI-11 routing flip, `doc1c` after ME-17) — complete them when the Gantt says so; do **not** treat `doc1b`/`doc1c` as the Sprint 2 / Sprint 3 **section** boundary. Other plans: read their Gantt section order verbatim.

## Step 3 — Post-flight (after all todos except `verify` are complete)

1. Run the plan's `verify` task (typically a 7-day observation window — query telemetry tables, sample misclassification audits, confirm cost matches)
2. If `verify` PASS → tell human "Plan complete, ready for /deploy"
3. Do NOT dispatch `devops-agent` from this command. Production deploy is a separate explicit human approval.

## Plan-specific quirks

The PLAN file body (not this command) is the authoritative source for special handling — paired tasks, shadow modes, decision-gate experiments, etc. Read the plan's "Sequencing" + "Sprint" sections carefully before each task.

## What this command does NOT do

- Does not modify the plan file (escalate to human if amendment needed)
- Does not push to main without explicit approval
- Does not deploy to production
- Does not skip QA — ever
