# RAD — Rapid App Development (PWA + Native)

RAD is a multi-agent development template for Cursor that ships production-ready **web apps (React Router v7 + Vite)** and, when your northstar calls for it, **Expo native clients** that share types and API code with the web app. You define the product. Figma Make designs it. A coordinated team of AI agents builds it — backend, frontend, mobile (when applicable), QA, design, devops, and research — each with narrow boundaries, structured handoffs, and human approval gates.

RAD is not a framework or a library. It is a set of agent instructions, slash commands, skills, and quality checks that turn Cursor into a managed development team. The human acts as Tech Lead — making architectural decisions, approving gates, and steering the product. The agents do the construction.

**This repository** is the native-capable template: it includes `mobile/` (Expo) and `shared/` (cross-platform types, validation, Supabase factory) so monorepo wiring stays consistent. The main web app (`src/routes`, root `package.json`, full Vite setup) is completed when you run **`/init`** after Phase 1 — see `RAD-GUIDE.md` for the full sequence.

## What RAD Solves

Building an app with AI agents without structure produces inconsistent, fragile output. Agents guess at architecture, skip edge cases, hallucinate integrations, and build features that contradict each other. RAD solves this by:

- **Constraining each agent to a narrow domain** — the backend agent never touches frontend code, the frontend agent never writes migrations, the QA agent never self-resolves security decisions. Each agent reads only the files it needs and produces only the artifacts it owns.
- **Enforcing a linear pipeline with gates** — no phase starts until the previous phase is approved. The northstar is validated before scaffolding. The tech spec is approved before building. Each feature passes QA before the next wave starts. No agent self-proceeds.
- **Making the design the source of truth** — Figma Make generates a complete working React app with mock data. The frontend agent's job is integration (swap mocks for real Supabase queries), not construction. This eliminates the "AI rewrote my UI" problem — 90% of Make's code stays untouched.
- **Validating technical decisions before code** — a complexity scan identifies features that need research (billing, real-time, complex auth). The Research Agent investigates implementation patterns on the specific stack. The tech spec documents every non-trivial decision with options considered, research basis, and revisit triggers.
- **Catching problems at every layer** — 66 automated rule checks, per-feature health scores, schema anti-pattern checklists, structured dogfooding, and a security audit before every deploy.

## Stack

**Web:** React Router v7 (Vite) · Supabase · TanStack React Query · Vercel · Tailwind CSS · Figma Make  

**Native (when deployment mode is `native` or `pwa-then-native`):** Expo · Expo Router · NativeWind · FlashList · react-native-reusables patterns · workspace packages `mobile` + `shared`

This matches how [React Native documents getting started today](https://reactnative.dev/docs/getting-started): they steer new apps toward a **framework** path, and the official [environment setup](https://reactnative.dev/docs/environment-setup) recommends **Expo**. Use the **[Expo documentation](https://docs.expo.dev/)** as the day-to-day reference ([Expo Router](https://docs.expo.dev/router/introduction/), [EAS Build & Submit](https://docs.expo.dev/eas/), [environment setup](https://docs.expo.dev/get-started/set-up-your-environment)). **Prerequisites and link tables** for humans are in `RAD-GUIDE.md` → **React Native and Expo**.

Deployment mode (`pwa`, `native`, or `pwa-then-native`) is locked in northstar §7c and validated in `/office-hours`. See **Deployment Mode** in `RAD-GUIDE.md`.

## How It Works

You talk to a **Tech Lead** agent in Cursor. It orchestrates specialist subagents — backend, frontend, **mobile** (when not PWA-only), QA, product design, devops, and research — each with a narrow domain, defined inputs, and structured outputs. Slash commands dispatch the right agent with the right context. You approve gates. Agents build.

The key insight: **Figma Make produces a complete working React app with mock data.** The frontend agent copies Make's files directly into route files, then applies targeted edits — swap mock data for Supabase queries, fix import paths, add loading/error/empty states. Layout, styling, and animations stay untouched. This cuts screen build time from hours to minutes.

## Principles

Three principles shape every agent's behavior:

1. **Completeness is cheap.** AI makes the marginal cost of the full implementation near-zero. Always do the complete thing — all edge cases, all states, all tests. The delta is minutes.
2. **Search before building.** Check if Supabase, React Router, TanStack, or Tailwind has a built-in before rolling custom. Three knowledge layers: tried-and-true, new-and-popular, first-principles.
3. **User sovereignty.** Agents recommend, the human decides. No agent self-proceeds past a blocking gate.

## Safety

- **Destructive command guardrails** — shell hooks intercept `rm -rf`, `DROP TABLE`, `git push --force`, and other destructive patterns before execution.
- **Security audit** — OWASP Top 10, RLS verification, secrets scanning, and dependency supply chain checks run before every production deploy.
- **Self-regulation** — QA fix loops track a WTF-likelihood score. If fixes start causing more problems than they solve, the agent stops and escalates.
- **Escalation protocol** — any agent can stop and say "this is too hard." Three failed attempts on the same task triggers automatic escalation.

---

## Quick Start

### One-Time Setup

**Accounts:**
- [ ] [Supabase](https://supabase.com) — two projects: dev + production
- [ ] [Vercel](https://vercel.com) — connect GitHub
- [ ] [Figma](https://figma.com) — access to Figma Make
- [ ] Payment provider (if monetizing) — test mode keys
- [ ] [Resend](https://resend.com) (if sending email) — API key

**Cursor settings:**
- [ ] Auto-run terminal commands → On
- [ ] Auto-apply edits → On
- [ ] Model: Claude Sonnet 4 (or latest)

**Global MCP** — add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

### Create Your Repo

Use this repo as your starting point (clone or GitHub template), or copy from the upstream RAD-React template:

```bash
# Example: create from your fork or organization template, or clone this repo and re-init remote
gh repo create [app-name] --private --clone
cd [app-name]
# copy template files in, or: gh repo clone your-org/RAD-PWA-Native [app-name]
```

To refresh core files from the upstream **RAD-React** web template only, run `scripts/populate-from-rad-react.sh` (see `--help`). That script does not add `mobile/` / `shared/` — use this native template when you want those workspaces pre-seeded.

### Build Sequence

| Step | Command | What happens | Gate |
|---|---|---|---|
| 1 | _(external)_ | Write northstar + EDS in Claude.ai / Gemini / any collaborative tool | Place in `artifacts/docs/` |
| 2 | `/office-hours` | Validate northstar structure + stress-test the idea | All 12 sections pass |
| 3 | `/init` | Scaffold project, install deps, link Vercel | Fill `.env.local` + MCP tokens |
| 4 | `/phase2` | Screen specs + Figma Make brief | Approve, then design in Make |
| 5 | _(manual)_ | Copy Make code to `src/make-import/` | — |
| 6 | `/phase4` | Tech spec (complexity scan → targeted research → invariants → schema → contracts) | Approve |
| 7 | `/setup` | Build plan with feature dependency graph | Approve |
| 8 | `/foundation` | Backend infra → Web foundation (+ native foundation when mode ≠ `pwa`) | Auto |
| 9 | `/feature [name]` | Backend → Frontend (+ Mobile when applicable) → QA per feature | Approve each QA PASS |
| 10 | `/visual-audit [url]` | Visual fidelity check on staging | Fix BLOCKING items |
| 11 | `/dogfood` | Human uses staging app, records findings | Fix BLOCKING items |
| 12 | `/pre-handoff` | Security audit + quality review | Approve |
| 13 | `/deploy [ref]` | Push to production | Smoke check |
| _Phase B_ | `/native-init` | _(only `pwa-then-native`)_ Extract shared code, wire Expo, translate screens after PWA ships | Per `RAD-GUIDE.md` |

See `RAD-GUIDE.md` for detailed instructions at each step.

---

## Architecture

```
Web (React Router v7 on Vercel)        Supabase (sole backend)
├── Vite + Tailwind                     ├── Postgres + RLS
├── TanStack React Query                ├── Auth (email, OTP, OAuth)
├── Pre-rendered landing at /           ├── Edge Functions (LLM, webhooks, cron)
├── SPA for /app/* (auth-guarded)       ├── Storage
├── Make TSX → route files              └── Realtime (if needed)
├── @supabase/supabase-js
└── imports shared types + API helpers from workspace package `shared`

Native (optional — Expo, EAS)
├── Expo Router screens
├── NativeWind + shared design tokens
├── `shared` package (types, validation, Supabase factory)
└── App Store / Play releases via EAS
```

No server runtime in the web client. No Next.js API routes. RLS is the single authorization boundary for data. Edge Functions handle anything needing server-only keys. **`shared`** is the seam where web and native stay aligned on contracts and Supabase usage.

---

## Agent Team

| Agent | Domain | Invoked via |
|---|---|---|
| **Tech Lead** | Orchestration, architecture, gates | Main Cursor session |
| **Product Designer** | Screen specs, Make briefs, visual QA | `/phase2`, `/visual-audit` |
| **Backend Developer** | Schema, migrations, RLS, Edge Functions | `/foundation`, `/feature` |
| **Frontend Developer** | Web screen integration, components, responsive PWA | `/foundation`, `/feature` |
| **Mobile Developer** | Expo screens (hybrid translation from Make web TSX), native UX | **`/foundation`** (mobile shell) + **`/feature [name]`** (Step 2b per feature). No separate `/mobile` command — see below. |
| **QA Agent** | Feature validation, health scoring, security audit | `/feature`, `/pre-handoff` |
| **DevOps Agent** | Production deploy | `/deploy` |
| **Research Agent** | Integration docs + technical pattern research | `/research`, auto from `/phase4` |

All agents follow standardized protocols: structured question format, completion status signals (DONE / BLOCKED / NEEDS_CONTEXT), and the escalation rule. Details: `AGENTS.md`.

---

## Quality Infrastructure

- **Northstar validation + stack fit** — `/office-hours` validates all 12 required sections plus checks product requirements against known stack constraints (Edge Function timeouts, Realtime connection limits, file processing caps). Mismatches are flagged before any code is written.
- **Technical complexity scan** — Phase 4 scans features against a checklist of complexity signals (money/credits, real-time, file processing, complex auth, search, state machines). Features with signals get targeted research before the spec is written.
- **Selective technical research** — the Research Agent handles both external integrations (Mode 1) and implementation pattern research (Mode 2). Complex features get domain-specific pattern docs that directly inform the schema design.
- **Architecture reference** — the Tech Lead has a knowledge base (`.cursor/skills/architecture/SKILL.md`) with stack constraints, domain patterns (credit billing, subscriptions, multi-tenant, social feeds), and a technical decision template.
- **Data invariants** — Phase 4 enumerates business rules (what must always be true) before designing the schema. Invariants drive CHECK constraints, indexes, and RLS policies.
- **Schema anti-pattern checklist** — 15 checks against known failure modes: missing transaction logs, incorrect cascades, race conditions, RLS gaps, missing indexes.
- **66 automated rule checks** — banned patterns, copy-then-edit enforcement, TanStack usage, CORS, staleness detection. Runs on every agent stop.
- **Per-feature health scores** — weighted across visual fidelity, data/perf, security, interaction flows, build/tests, and copy. Stored as `baseline.json` for regression comparison.
- **Diff-aware QA** — scopes testing to changed files and affected routes.
- **Structured dogfooding** — between visual audit and pre-handoff, the builder uses the staging app for 30–60 minutes with a generated task list, records findings, and validates assumptions from office hours.
- **Root cause investigation** — complex bugs use a 4-phase protocol: investigate → analyze → hypothesize → implement.
- **Atomic commits** — one commit per fix, bisect-friendly history.

---

## Kicking off native app development

There is **no** `/mobile` slash command. The **Mobile Developer** is always launched by the Tech Lead **inside** other commands, so native stays in sync with backend and web.

| Path | What you run | What triggers Mobile Developer |
|---|---|---|
| **`native`** (mobile from day one) | After **`/init`**, run **`/foundation`** then **`/feature [name]`** for each planned feature. | **`/foundation`** — after web foundation, dispatches *Foundation — Mobile App Setup* (Expo shell, providers, auth screens, dev client). **`/feature [name]`** — *Step 2b — Mobile* runs after web frontend for that feature (in `native` mode, web Step 2 is often landing-only; app UI lands on mobile in Step 2b). |
| **`pwa-then-native`** Phase B | When the PWA is shipped, run **`/native-init`** once (workspaces + shared extraction + Expo scaffold), then **`/foundation`** (mobile shell is included when mode is not PWA-only), then **`/feature [name]`** for each feature. | **`/native-init`** only prepares the repo — it does **not** build screens. Mobile work still goes through **`/foundation`** and **`/feature`**. |

Details live in `.cursor/commands/foundation.md` (Mobile Foundation), `.cursor/commands/feature.md` (Step 2b), and `.cursor/commands/native-init.md` (Phase B scaffold).

---

## Command Reference

| Command | What it does |
|---|---|
| `/office-hours` | Validate northstar + product diagnostic + stack fit check |
| `/init` | Scaffold project, install deps, configure MCP |
| `/phase2` | Screen specs + Figma Make brief |
| `/phase4` | Tech spec (complexity scan → research → invariants → schema → decisions → contracts) |
| `/setup` | Generate build plan with feature context packages |
| `/foundation` | Backend + web foundation; **if mode ≠ `pwa`**, also dispatches **Mobile Developer** for the Expo shell |
| `/feature [name]` | **Backend → Frontend → (Mobile Step 2b if mode ≠ `pwa`) → QA** — see `.cursor/commands/feature.md` |
| `/native-init` | **`pwa-then-native` Phase B only:** extract `shared/`, wire Expo — run **before** mobile **`/foundation`** / **`/feature`** |
| `/visual-audit [url]` | Visual fidelity check on staging |
| `/dogfood` | Structured product testing by the builder |
| `/pre-handoff` | Security audit + quality review |
| `/deploy [ref]` | Production deploy |
| `/session-start` | Restore context after session drop |
| `/session-end` | Save session memory |
| `/status` | Diagnostic — phases, features, health |
| `/research [name]` | Research external integrations |
| `/regen-feature [name]` | Regenerate feature context after amendment |

---

## File Structure

After **`/init`**, the root has a standard Node workspace: root `package.json` (with `workspaces: ["mobile", "shared"]` when deployment mode is `native` or `pwa-then-native`), lockfile, and the full Vite + RR7 tree under `src/`. This template may ship with a minimal `src/` until init runs; `mobile/` and `shared/` are present for native workflows.

```
src/                         Web app (expanded by /init)
  routes/
    _index/route.tsx         Landing page (pre-rendered for SEO)
    _auth/                   Login, signup, OAuth callback
    _app/                    Authenticated screens (auth guard layout)
      [feature]/route.tsx    Feature screens (integrated from Make)
  components/
    ui/                      Make's UI primitives (copied as-is)
  hooks/                     useAuth, useProfile, useInstallPrompt, etc.
  lib/
    supabase.ts              Web client (uses shared factory when extracted)
    auth.tsx                 AuthProvider + useAuth
    api-types.ts             May re-export from shared in monorepo mode
    database.types.ts        Auto-generated / synced with shared
    data/                    Typed query functions

shared/                      Workspace package — types, validation, `shared/api` (Supabase factory)
mobile/                      Workspace package — Expo Router app (depends on `shared`)

supabase/
  migrations/                SQL schema + RLS policies
  functions/                 Edge Functions
  seed.sql                   Dev seed data

artifacts/
  docs/                      Planning docs + ETHOS.md
  plans/                     Build plan + project tracker
  qa-reports/                Health scores + dogfood report
  issues/                    Issue tracking
  integrations/              External API research docs

.cursor/
  agents/                    Specialist agent definitions
  commands/                  Slash commands (including /native-init, /office-hours, /dogfood)
  rules/                     Auto-injected behavioral constraints
  skills/                    Architecture reference, Phase 1 template, investigation, security audit, testing
  hooks/                     Destructive command guardrails, agent-stop checks

scripts/
  populate-from-rad-react.sh Optional: sync core template from upstream RAD-React repo
```
