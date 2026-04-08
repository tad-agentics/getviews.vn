# /status

Diagnostic: report current phase completion, feature status, build health, and open issues.

## Steps

1. Read `artifacts/plans/project-plan.md`
2. Read `agent-workspace/ACTIVE_CONTEXT.md`
3. Read `artifacts/docs/changelog.md` — count BLOCKING and NON-BLOCKING items
4. List files in `artifacts/issues/` — count open issues
5. Run `git log --oneline -15`
6. Run `npm run build` — report pass/fail

## Report format

```
## Project Status — [App Name] — [YYYY-MM-DD]

### Planning Phases
Phase 2 (Wireframes):     [✓ complete | in progress | not started]
Figma Make:            [✓ code copied to src/make-import/ | not started]
Phase 4 (Tech Spec):      [✓ complete | in progress | not started]
Setup:                    [✓ complete | in progress | not started]

### Foundation
Backend infra:            [✓ [commit] | not started]
Shared components:        [✓ [commit] | not started]

### Feature Workstreams
[Feature name]  Wave [N]  Backend: [✓/in progress/queued]  Frontend: [✓/in progress/queued]  QA: [✓ PASS/in progress/queued]

### Build Health
npm run build:            [✓ PASS | ✗ FAIL — [error count] errors]
Open issues:              [count] ([N] BLOCKING, [N] NON-BLOCKING)
Changelog blocking items: [count]

### Recent commits
[last 5 from git log]

### Next action
[what should happen next based on current state]
```
