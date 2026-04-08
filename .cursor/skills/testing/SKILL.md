---
name: testing
description: Per-feature QA checklist — validates a complete feature before marking it done. Invoked by the QA Agent during /feature workstreams.
disable-model-invocation: true
---

# Testing — Per-Feature QA Checklist + Rule Validation

## Rule Validation (run after editing any .mdc, agent, or command file)

```bash
bash .cursor/skills/testing/scripts/validate-rules.sh
```

66 automated checks covering: banned patterns (11), copy-then-edit enforcement (4), TanStack React Query (5), LLM/OpenRouter (4), Edge Function CORS (3), visual fidelity (2), QA adversarial passes (2), stack consistency (1), foundation step numbering (1), .mdc file sizes (5), data fetching anti-patterns (2), staleness & cross-reference checks (19+: shared protocols in agents, ETHOS.md, investigate skill, qa-reports dir, destructive hooks, stale paths, phase1 skill, office-hours mandatory gate, dogfood command, tech-spec invariants, tech-spec anti-pattern checklist, architecture skill, complexity signals, stack constraints, office-hours stack fit, research agent Mode 2, tech-spec complexity scan, tech-spec technical decisions).

**Test-driven rule development workflow:**
1. When a live-test reveals an agent mistake, add a check to `validate-rules.sh` FIRST
2. Then fix the .mdc or agent file
3. Re-run `validate-rules.sh` — must pass 40/40
4. This prevents regressions: the same mistake can never return silently

## Feature QA (run after feature frontend commits)

First, run the automated build checks:

```bash
bash .cursor/skills/testing/scripts/run-checks.sh
```

If the script exits with an error, fix all failures before proceeding. Do not mark a feature complete with a failing build.

Then verify every screen in the feature manually:

- Component renders without errors in default state
- All interaction states covered: default / loading / error / empty
- **Interaction flow** — every step in the screen spec metadata block executes correctly:
  - Each branch condition (credit check, profile exists) leads to the correct UI state
  - Paywall gates show partial result + correct credit cost + purchase action
  - After payment, full result renders without page reload
- Data variables inject correctly with real values (not placeholders)
- Data fetched via Supabase client hooks (`src/hooks/`) or query functions (`src/lib/data/`) — no inline `supabase.from()` calls in JSX render paths
- Mutations use Supabase client in event handlers or custom hooks — no raw `fetch()` calls
- **RLS validation** — verify data is scoped to current user:
  - Attempt to access another user's data by modifying URL params — should return empty or redirect
  - Verify inserts set `user_id` correctly via RLS (no manual user_id assignment in frontend)
  - Check browser DevTools Network tab — no Supabase errors indicating RLS policy violations
- **Auth guard** — navigate directly to `/app/[route]` without session → should redirect to `/login`
- **Copy quality** — every visible string passes the 5-question Copy Quality Test from `copy-rules.mdc`. No placeholder text, no `{{COPY:context}}` tokens remaining, no forbidden words.
- **Dopamine moments** — if screen metadata flags D1/D2/D3/D4: animation timing, easing, stagger match EDS §6. Post-moment delay before CTAs is respected.
- Passes on mobile viewport (375px)
- Navigation: enters from correct screen, exits to correct screen per screen spec metadata
- No console errors or warnings in default state
- Acceptance criteria from `artifacts/plans/build-plan.md` [feature context package] all pass
- `npm run build` — 0 TypeScript errors
