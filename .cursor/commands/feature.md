# /feature [name]

Dispatch a complete feature workstream: Backend → Frontend → QA in sequence.
Each step runs as a foreground subagent and must commit before the next is dispatched.

Usage: `/feature auth` or `/feature goal-creation`

## Pre-flight checks

Before dispatching, confirm:
- [ ] Feature `[name]` exists in `artifacts/plans/build-plan.md`
- [ ] Foundation is committed (`feat(foundation): backend infrastructure complete` + `feat(foundation): shared components + landing page + auth screens complete`)
- [ ] All features this one depends on are committed and QA-passed (check build-plan.md dependency graph)
- [ ] `npm run build` passes on current state

If any check fails: report to human, do not dispatch.

## Step 1 — Backend

Launch Backend Developer subagent (foreground):

```
Task: Feature [name] — Backend

Read:
- .cursor/agents/backend-developer.md (your full instructions)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/tech-spec.md
- artifacts/plans/build-plan.md — read the [name] feature context package specifically

Mode: Feature
Build the backend for the [name] feature only — migration, RLS, data hooks, Edge Functions (if needed).
Most features are client → RLS direct and need no Edge Functions.
Signal completion when feat([name]): backend complete is committed.
```

Wait for `feat([name]): backend complete` commit before proceeding.

## Step 2 — Frontend

Launch Frontend Developer subagent (foreground):

```
Task: Feature [name] — Frontend

Read:
- .cursor/agents/frontend-developer.md (your full instructions)
- .cursor/rules/copy-rules.mdc (copy formula, quality test — enforce on all copy)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/plans/build-plan.md — read the [name] feature context package specifically
- artifacts/docs/screen-specs-[app]-v1.md — screens for this feature only (metadata: interaction flows, dopamine moment flags, production-ready copy slots, credit costs)
- artifacts/docs/design-system-spec.md
- artifacts/docs/emotional-design-system.md — read §6 if any screen has a dopamine moment flag (D1–D4)

Mode: Feature
For each screen: COPY from **`artifacts/uiux-reference/screens/`** (or optional `src/make-import/screens/`) into the route file. Then apply targeted str_replace edits per frontend-make.mdc (fix imports, swap mock data → Supabase queries, swap mock auth → useAuth). Do NOT rewrite any Make file from scratch — 90% of Make's code stays untouched.
- Implement interaction flows exactly as specified in screen spec metadata
- Copy slots are production-ready — use verbatim
- Add loading/error/empty states below existing JSX (Make output only has happy path)
- Every Tailwind class, animation, and layout decision from Make must be preserved exactly

Mutation Patterns (mandatory):
- Every useMutation must invalidate ALL affected query keys in onSuccess. Over-invalidate when in doubt.
- Optimistic UI for user-facing actions (toggle, add, submit) — update cache in onMutate, rollback in onError, refetch in onSettled.
- NO optimistic UI for credit deductions or payment actions — wait for server confirmation.
- See frontend-data.mdc "Mutation Cache Invalidation" and frontend.mdc "Common Agent Mistakes" for full patterns.

Signal completion when feat([name]): screens complete is committed.
```

Wait for `feat([name]): screens complete` commit before proceeding.

## Step 2b — Mobile (mode ≠ pwa only)

If deployment mode is `native` or `pwa-then-native` Phase B, launch Mobile Developer subagent:

```
Task: Feature [name] — Mobile Screens

Read:
- .cursor/agents/mobile-developer.md (your full instructions)
- .cursor/rules/mobile.mdc (prohibitions + NativeWind rules — read FIRST)
- .cursor/rules/copy-rules.mdc (copy quality test — enforce on all copy)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/plans/build-plan.md — read the [name] feature context package
- artifacts/docs/screen-specs-[app]-v1.md — screens for this feature (Mobile Navigation metadata)
- artifacts/docs/make-reference/ — Make .tsx files for screens in this feature

Mode: Feature
For each screen: run 3-phase hybrid translation from Make's web TSX.
  Phase A: Extract types, mock data, copy strings → shared/
  Phase B: Element swaps, class filtering, Radix→@rn-primitives
  Phase C: Navigation, scroll, keyboard, safe area, haptics
Add loading/error/empty states. Wire TanStack Query hooks from shared/hooks/.
Copy slots are production-ready — use verbatim.

Signal completion when feat([name]): mobile screens complete is committed.
```

For `native` mode: Step 2 (web Frontend) builds landing page only. Step 2b builds all app screens.
For `pwa-then-native` Phase B: skip Step 2 entirely — web screens already exist from Phase A.

Wait for mobile commit before proceeding to QA.

## Step 3 — QA

Launch QA Agent subagent (foreground):

```
Task: Feature [name] — QA

Read:
- .cursor/agents/qa-agent.md (your full instructions)
- .cursor/rules/copy-rules.mdc (copy quality test — validate all screen copy)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/tech-spec.md
- artifacts/plans/build-plan.md — read the [name] acceptance criteria specifically
- artifacts/docs/screen-specs-[app]-v1.md — metadata for this feature's screens
- artifacts/docs/emotional-design-system.md — §6 dopamine specs if any screen has a D1–D4 flag

Mode: Feature
Run all 5 verification passes (Visual Fidelity, Data & Performance, Security & RLS, Interaction Flows, Build & Test).
After all passes: run the adversarial cross-check to strip false positives.
Signal PASS (all 5 clean) or BLOCKING (items grouped by pass number).
```

## After completion

**If PASS:**
1. Update `artifacts/plans/project-plan.md` — mark feature complete
2. Update `agent-workspace/ACTIVE_CONTEXT.md`
3. Report to human: "Feature [name] complete ✓. [Next wave features / All Wave N done]"

**If BLOCKING:**
1. Create `artifacts/issues/[feature-name]-[short-description].md`
2. Report to human with blocking list
3. After fix: re-run Step 3 (QA only)
