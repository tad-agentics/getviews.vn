# /setup

Tech Lead scaffolds the project and generates the build plan. Runs after Phase 4 is approved and Make code is in `src/make-import/`.

## Pre-flight checks

Before starting, confirm:
- [ ] `artifacts/docs/tech-spec.md` exists
- [ ] `src/make-import/` exists with Make's code output (human has copied from Make's Code tab)
- [ ] `artifacts/docs/screen-specs-[app]-v1.md` exists
- [ ] `artifacts/plans/build-plan.md` is still the placeholder (not yet generated)
- [ ] `npm run build` passes (or `package.json` exists with base dependencies installed)

If any check fails: report to human, do not proceed.

## Steps

### 1. Write `project.mdc`

Fill in `.cursor/rules/project.mdc` using the template already in the file:
- App name
- What the app does (from northstar)
- Not building list (from northstar)
- LLM rules (from tech-spec)
- AI module boundary (if AI features — note Edge Function pattern for server-only API keys)
- Key constraints

### 2. Add integration MCPs

Base MCP servers (Supabase, Vercel, Context7) were added during `/init`. Check `artifacts/docs/tech-spec.md` Section 5 (External Integrations) for third-party services that require additional MCP servers. Add them to `.cursor/mcp.json`:

- Payment provider MCP — if tech-spec lists a payment integration (Stripe MCP, etc.)
- Any other provider with an available MCP server

Present additions to the human for credential fill-in. Never commit `.cursor/mcp.json`.

### 3. Verify app-specific npm packages

Check `package.json` for packages required by this app's tech stack (from tech-spec §5 and §6). Report any missing ones to the human:
- Payment SDK — from tech-spec §5: install the SDK for the payment provider specified (e.g., `stripe` for Stripe, `payos` for PayOS). Do not default to Stripe.
- Email SDK (`resend`) — if tech-spec Section 16 (Email Flows) is present
- LLM calls go through OpenRouter API (OpenAI-compatible) in Edge Functions — no frontend SDK needed
- Animation libraries (`motion`, `react-countup`) — if EDS §6 Dopamine Moments require them (check if installed during /init)
- Any other integration SDK listed in tech-spec §5

Base packages (`@supabase/supabase-js`, `zod`) were installed during `/init` — do not re-install.

### 4. Generate `artifacts/plans/build-plan.md`

This is the most important step. Read:
- `artifacts/docs/northstar-[app].html` — §7 Build Scope, §7b Landing Page Content, §12 Feature Grouping (wave structure), §13 User Scenarios (if present)
- `artifacts/docs/tech-spec.md` — tables, RLS, data hooks, Edge Functions per feature, §18 SEO & PWA Infrastructure (Foundation context)
- `artifacts/docs/screen-specs-[app]-v1.md` — screens per feature (metadata blocks: components, data vars, states, interaction flows, dopamine moments, copy slots, credit costs) + landing page
- `artifacts/docs/emotional-design-system.md` — copy register, dopamine moment specs

Produce `artifacts/plans/build-plan.md` with:
1. **Feature Dependency Graph** — **if northstar §12 defines waves, use that structure directly.** Otherwise, derive: Foundation always first → Wave 1: auth + profile → Wave 2+: features requiring authenticated user → Wave 3+: billing, retention, social.
2. **Foundation context package** — always first, includes:
   - Backend: static SEO files (robots.txt, sitemap.xml, manifest.json) + Supabase client, schema, auth provider, Edge Functions (if webhooks/email in scope)
   - Frontend: landing page from screen specs + northstar §7b + auth screens + custom shared components from design-system-spec.md + useInstallPrompt hook
   - The landing page is the first screen built — validates tokens, components, and install flow
3. **Per-feature context packages** — for each feature, extract and compile:
   - Backend context: exact tables, RLS intent, data hooks, Edge Functions (if needed)
   - Frontend context: exact screens with metadata (components, data vars, states, interaction flows with branch conditions, Make component names for copying)
   - Copy: production-ready copy slots from screen spec metadata, tagged with context type
   - Dopamine moments: which screens have D1–D4 flags, reference EDS §6
   - Credit costs: which screens have paywall gates, exact credit amounts
   - Acceptance criteria

Each context package must be self-contained.

### 5. Verify `supabase/seed.sql`

Seed data was written during `/phase4`. Verify it exists and covers at least one test user profile + sample rows for each core entity.

### 6. Update `artifacts/plans/project-plan.md`

- Mark Setup complete
- Populate the Feature Workstreams table

## After completion

Present to human:
```
Setup complete.

project.mdc written — review and confirm app context is correct.
build-plan.md generated — [N] features across [N] waves.
Integration MCPs added to .cursor/mcp.json — add any new credentials before proceeding.

When ready: approve this gate to begin Foundation.
```

Commit: `chore(setup): scaffold + rules + seed + build plan`
