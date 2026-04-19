# AGENTS.md — RAD Multi-Agent Team

> Tech Lead reads this file as the primary reference. Specialist agents read their own `.cursor/agents/` files and auto-injected rules. This file defines the team structure, workflow, and shared conventions.

---

## Stack

React Router v7 (Vite) · Supabase (DB + Auth + RLS + Edge Functions + Storage) · TanStack React Query · Vercel · Tailwind CSS · Studio UIUX (`artifacts/uiux-reference/`)

---

## Rule Authority (when files conflict)

Multiple files contain overlapping rules. When they disagree, follow this precedence — highest wins:

1. **`.cursor/rules/*.mdc`** — auto-injected behavioral constraints. These are the law. If a `.mdc` rule contradicts an agent file or skill file, the `.mdc` rule wins.
2. **`.cursor/agents/*.md`** — agent-specific workflow and deliverables. Defines what to build and in what order.
3. **`.cursor/skills/*.md`** — detailed phase instructions and output templates. Defines how to build a specific artifact.
4. **`.cursor/commands/*.md`** — dispatch orchestration. Defines the sequence of agent invocations.

In practice: `.mdc` rules define the code standards. Agent files define the work. Skill files define the artifact format. Commands define the workflow. If an agent file says "create an Edge Function" and `backend.mdc` says "Edge Functions use Deno.serve with signature verification," the agent creates the function with that pattern.

---

## Agent Team

| Agent | Role | Agent file | Invoked via |
|---|---|---|---|
| **Tech Lead** | Human-facing orchestrator. Owns architecture, state, and approvals. | _(main Cursor session)_ | Direct |
| **Product Designer** | Screen planning + Figma Make prompt guidance + visual QA. | `product-designer.md` | `/phase2`, `/visual-audit` |
| **Backend Developer** | DB schema, migrations, RLS, Edge Functions, webhooks, cron. | `backend-developer.md` | `/foundation`, `/feature` |
| **Frontend Developer** | Screens (copied from Figma Make TSX), shared components, mobile viewport. | `frontend-developer.md` | `/foundation`, `/feature` |
| **Mobile Developer** | Native screens (translated from Make TSX via hybrid 3-phase), NativeWind, react-native-reusables, FlashList. | `mobile-developer.md` | `/foundation`, `/feature` (mode ≠ pwa) |
| **QA Agent** | Feature validation + pre-handoff safety audit. | `qa-agent.md` | `/feature`, pre-handoff |
| **DevOps Agent** | Production deploy. Runs once after QA sign-off. | `devops-agent.md` | `/deploy` |
| **Research Agent** | Technical research — integration docs + implementation pattern research. | `research-agent.md` | `/research`, auto from `/phase4` and `/new-feature` |

The human communicates exclusively with the Tech Lead. Sub-agents never communicate with the human directly.

---

## Agent Dispatch

All specialists are used proactively. When choosing which subagent to launch:

| Task | Subagent |
|---|---|
| Any backend work — tables, migrations, RLS, Edge Functions, logic changes | `backend-developer` |
| Any UI work — screens, components, interactions, navigation, styling | `frontend-developer` |
| Any native mobile UI work — Expo screens, NativeWind, react-native-reusables (mode ≠ pwa) | `mobile-developer` |
| Validate a completed feature end-to-end | `qa-agent` |
| Any design work — screen specs, Make prompts, visual audit | `product-designer` |
| Any deployment work | `devops-agent` |
| Research an external integration (API docs, SDK, webhooks) | `research-agent` (Mode 1) |
| Research implementation patterns for complex features (concurrency, auth, billing) | `research-agent` (Mode 2) |
| Complex bug investigation (root cause unclear, fix spans >3 files) | Tech Lead uses `.cursor/skills/investigate/SKILL.md` |
| Security audit before deploy (OWASP + RLS + secrets + deps) | QA Agent uses `.cursor/skills/security-audit/SKILL.md` |

---

## Workflow

| Phase | Command | Who | Gate |
|---|---|---|---|
| **Phase 1** | _(external)_ | Human (Claude.ai, Gemini, etc.) | Northstar + EDS placed in `artifacts/docs/` |
| **Office Hours** | `/office-hours` | Tech Lead | Northstar validated — all 12 sections pass + stack fit check |
| **Init** | `/init` | Tech Lead | Phase 1 artifacts present + validated |
| **Phase 2** | `/phase2` | Product Designer | Human approves screen specs + Figma Make brief |
| **UIUX reference** | _(repo-tracked)_ | `artifacts/uiux-reference/` | Shell + screens + `styles.css` — primary design map (optional legacy dump in gitignored `src/make-import/`) |
| **Phase 4** | `/phase4` | Tech Lead | Human approves tech spec |
| **Setup** | `/setup` | Tech Lead | Human approves build plan |
| **Foundation** | `/foundation` | Backend (infra + SEO/PWA) → Frontend (Make import + component inventory + Tailwind config + landing + auth) | Auto-proceeds after commit |
| **Features** | `/feature [name]` | Backend → Frontend → QA (per feature, parallel waves) | Human approves each QA PASS |
| **Visual audit** | `/visual-audit [url]` | Product Designer | Fix all BLOCKING findings |
| **Dogfood** | `/dogfood` | Human (with Tech Lead) | Fix all BLOCKING findings |
| **Pre-handoff** | `/pre-handoff` | QA Agent | Human approves |
| **Deploy** | `/deploy [ref]` | DevOps Agent | — |

Blocking gates are enforced — no agent self-proceeds to the next phase.

---

## File Path Map

### Operational (gitignored)

| Path | Purpose |
|---|---|
| `agent-workspace/ACTIVE_CONTEXT.md` | Current focus + active workstreams — Tech Lead writes on each shift |
| `agent-workspace/memory/YYYY-MM-DD.md` | Daily session log — written at end of session, read at start |
| `agent-workspace/temp/` | Throwaway files (previews, scratch) — never committed |

### Artifacts (git-tracked)

| Path | Purpose |
|---|---|
| `artifacts/docs/northstar-[app].html` | Phase 1 input |
| `artifacts/docs/emotional-design-system.md` (or `eds-[app].html`) | Phase 1 input |
| `artifacts/docs/screen-specs-[app]-v1.md` | Phase 2 output — screen metadata (include a `## Make build brief` appendix when needed) |
| `artifacts/docs/design-system-spec.md` | Make component inventory (produced during Foundation) |
| `artifacts/docs/tech-spec.md` | Phase 4 output |
| `artifacts/docs/ETHOS.md` | Builder ethos — completeness, search-before-building, user sovereignty |
| `artifacts/docs/changelog.md` | Ongoing deviations from spec |
| `artifacts/plans/build-plan.md` | Feature dependency graph + per-feature context packages |
| `artifacts/plans/project-plan.md` | Phase + feature completion tracker |
| `artifacts/qa-reports/[feature]-baseline.json` | Per-feature QA health scores and findings — written by QA Agent |
| `artifacts/qa-reports/dogfood-report.md` | Dogfooding findings — written during `/dogfood` |
| `artifacts/issues/[issue-name].md` | Issue tracking — kebab-case, one file per issue |
| `artifacts/integrations/[name].md` | Integration research docs — one per external dependency, written by Research Agent |
| `artifacts/integrations/pattern-[name].md` | Technical pattern research docs — one per complex feature, written by Research Agent |
| `artifacts/docs/features/[name].md` | Feature docs for post-launch features — written during `/new-feature` |

### Source

| Path | Purpose |
|---|---|
| `artifacts/uiux-reference/` | Studio UIUX Upgrade pack (JSX + `styles.css` + `data.js`) — **tracked** design reference |
| `src/make-import/` | _(optional, gitignored)_ Legacy Figma Make dump if someone pastes one |
| `src/routes/_index/route.tsx` | Landing page (pre-rendered at build time for SEO) |
| `src/routes/_auth/login/route.tsx` | Login screen |
| `src/routes/_auth/signup/route.tsx` | Signup screen |
| `src/routes/_auth/callback/route.tsx` | OAuth callback handler |
| `src/routes/_app/layout.tsx` | Auth guard layout — checks session, redirects to /login |
| `src/routes/_app/[feature]/route.tsx` | Feature screen (copied from Figma Make TSX, targeted edits applied) |
| `src/routes/_app/[feature]/components/` | Route-specific components |
| `src/components/ui/` | Radix-style UI primitives (historically from Make import; treat as the app library) |
| `src/components/` | Shared components (used by 2+ screens) |
| `src/hooks/` | Shared hooks (`useAuth`, `useProfile`, `useInstallPrompt`) |
| `src/lib/supabase.ts` | Single Supabase client (publishable key) |
| `src/lib/auth.tsx` | AuthProvider context + useAuth hook |
| `src/lib/data/[entity].ts` | Typed query functions (optional organizational layer) |
| `src/lib/api-types.ts` | All shared TypeScript interfaces |
| `src/lib/database.types.ts` | Generated types from `supabase gen types` |
| `src/lib/formatters.ts` | Formatting utilities |
| `src/lib/constants.ts` | App-wide constants |
| `src/app.css` | Tailwind directives + @font-face + base styles + brand tokens (CSS custom properties from Make's theme.css) |
| `react-router.config.ts` | SPA mode, pre-render `/` |
| `vite.config.ts` | Vite + React Router + Tailwind + PWA |
| `vercel.json` | SPA rewrite rules |
| `public/manifest.json` | PWA manifest (static) |
| `public/robots.txt` | Crawl rules |
| `public/sitemap.xml` | Sitemap (static) |
| `public/fonts/` | Self-hosted font files |
| `public/icons/` | PWA icons |
| `supabase/migrations/` | SQL migration files |
| `supabase/functions/` | Edge Functions (webhooks, cron, email, service_role ops) |
| `supabase/seed.sql` | Dev seed data |

---

## Memory System

Agents have no cross-session memory. All state lives in two files that are updated **continuously** throughout the session — not just at the end. This ensures any agent can reconstruct full context even if the session drops without a clean `/session-end`.

### `agent-workspace/ACTIVE_CONTEXT.md`

The "you are here" file. Tech Lead updates this immediately on every focus shift, dispatch, completion, or blocker — not just at session boundaries. Template: `artifacts/templates/ACTIVE_CONTEXT.md`

### `agent-workspace/memory/YYYY-MM-DD.md`

One file per day. Linear append-only log — blocks are added as work progresses. Any agent can pick up mid-session and know exactly what has happened. If the session drops, context is never lost. Template: `artifacts/templates/memory-YYYY-MM-DD.md`

---

## Session Warm-Up

Any agent, any session, reconstructs full working context by reading:

```
1. Always-apply rules              ← auto-injected by Cursor (project.mdc + scoped rules)
2. agent-workspace/ACTIVE_CONTEXT.md
3. agent-workspace/memory/[today].md (+ yesterday's if early in the day)
4. Agent-specific reading list     ← defined in each agent's .cursor/agents/ file
```

---

## Commit Convention

### Phase-level commits (progress gates)

| Agent | Format | Example |
|---|---|---|
| Tech Lead (Phase 4) | `docs(phase4): tech spec complete` | — |
| Tech Lead (Setup) | `chore(setup): scaffold + rules + seed + build plan` | — |
| Tech Lead (Init) | `chore(init): project scaffold and workspace initialized` | — |
| Backend Developer (foundation) | `feat(foundation): backend infrastructure complete` | — |
| Frontend Developer (foundation) | `feat(foundation): shared components + landing page + auth screens complete` | — |
| Backend Developer (feature) | `feat([feature]): backend complete` | `feat(auth): backend complete` |
| Frontend Developer (feature) | `feat([feature]): screens complete` | `feat(goal-creation): screens complete` |
| QA Agent (feature) | `test([feature]): qa pass` | `test(billing): qa pass` |
| QA Agent (pre-handoff) | `test: pre-handoff review complete` | — |
| DevOps Agent | `chore(deploy): staging → main, production live` | — |

### Atomic commits (within fix loops)

Within any fix loop or multi-fix session, **one commit per fix.** Never bundle multiple fixes. Each commit must be independently revertable.

| Context | Format | Example |
|---|---|---|
| QA bug fix | `fix(qa): [feature]-ISSUE-NNN — short description` | `fix(qa): billing-ISSUE-003 — paywall gate bypassed on zero credits` |
| QA regression test | `test(qa): regression test for [feature]-ISSUE-NNN` | `test(qa): regression test for billing-ISSUE-003` |
| Any agent (amendment) | `fix: [short description per changelog]` | — |

### Bisect-friendly rule

Every commit should be a single logical change. When you've made multiple changes (e.g., a rename + a rewrite + new tests), split them into separate commits. Renames/moves separate from behavior changes. Test infrastructure separate from test implementations. Each commit should be independently understandable and revertable.
