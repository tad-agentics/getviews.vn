# /foundation

Dispatch Foundation subagents — backend infrastructure and shared components.
Runs after the Setup gate is approved.

## Pre-flight checks

Before dispatching, confirm:
- [ ] `artifacts/plans/build-plan.md` is fully generated (not the placeholder)
- [ ] `.cursor/mcp.json` credentials are configured
- [ ] `npm run build` passes on current state (no pre-existing errors)
- [ ] `git log` shows `chore(setup): scaffold + rules + seed + build plan` commit

If any check fails: report to human, do not dispatch.

## Dispatch — Backend Foundation

Launch Backend Developer subagent (foreground):

```
Task: Foundation — Backend Infrastructure

Read:
- .cursor/agents/backend-developer.md (your full instructions)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/tech-spec.md (including Section 18 — SEO & PWA Infrastructure)
- artifacts/docs/northstar-[app].html (§7b for landing page metadata, §5 for brand colors → manifest theme_color)
- artifacts/plans/build-plan.md

Mode: Foundation
Build all shared infrastructure as specified in the Foundation Mode section of your agent file.

Foundation backend includes:
- Supabase client (src/lib/supabase.ts), AuthProvider (src/lib/auth.tsx), types, hooks
- Schema migrations + RLS policies + seed data
- OAuth setup instructions (if applicable)
- Storage buckets + helpers (if applicable)
- Edge Functions: payment webhook, send-email (if applicable), LLM interpret/reason functions (all RAD apps)
- LLM cache table (llm_cache) in initial migration
- Set Edge Function secrets: `supabase secrets set OPENROUTER_API_KEY=...` (+ payment/email keys if applicable)
- Static SEO/PWA files:
  - public/robots.txt — allow /, disallow /app/
  - public/sitemap.xml — landing page at priority 1
  - public/manifest.json — name/short_name from northstar, theme_color from EDS §5, icons, screenshots
  - OG image solution (static PNG or Edge Function — per tech-spec §18)

Signal completion when feat(foundation): backend infrastructure complete is committed.
```

Wait for Backend Foundation to commit before dispatching Frontend Foundation.

## Dispatch — Frontend Foundation

After Backend Foundation commits, launch Frontend Developer subagent (foreground):

```
Task: Foundation — Make Import + Components + Tailwind + Landing Page + Auth Screens

Read:
- .cursor/agents/frontend-developer.md (your full instructions)
- .cursor/skills/design-system/SKILL.md (component inventory process)
- .cursor/rules/copy-rules.mdc (copy quality test for landing page copy validation)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/uiux-reference/ (tracked UIUX pack — read app.jsx + shell.jsx first; optional src/make-import/)
- artifacts/docs/emotional-design-system.md — §6 Dopamine Moments (check if motion/react-countup are needed)
- artifacts/docs/screen-specs-[app]-v1.md — landing page metadata block
- artifacts/docs/northstar-[app].html — §7b Landing Page Content
- artifacts/plans/build-plan.md

Mode: Foundation

Step 0: Install Make's dependencies — scan imports across Make's files (not just package.json). Run npm install [packages]. Verify npm run build passes.
Step 1: Ensure src/components/ui/ exists (copy from legacy src/make-import/components/ui/ if Foundation never ran). Catalog components and produce artifacts/docs/design-system-spec.md (per design-system SKILL.md). Build any missing shared pieces (EmptyState, ErrorBanner, SkeletonCard).
Step 2: Copy Make's theme.css (CSS custom properties + @theme inline) into src/app.css. Replace Google Fonts CDN imports with self-hosted .woff2. Fix next-themes import in sonner.tsx.
Step 3: Create src/lib/query-client.ts (QueryClient with default staleTime: 60s) and src/lib/query-keys.ts per frontend-data.mdc. Wrap app in QueryClientProvider in src/root.tsx. Create src/hooks/useCredits.ts shared hook.
Step 4: Create src/hooks/useInstallPrompt.ts (spec in tech-spec §18).
Step 5: Landing page (src/routes/_index/route.tsx) — if Make has a landing page, COPY the file directly and apply targeted edits. Otherwise build from northstar §7b.
  - Route: / (pre-rendered at build time)
  - Content from northstar §7b — all copy is production-ready, use verbatim
  - Section stack from screen spec metadata: hero, trust bar, benefits, how-it-works, social proof, FAQ, final CTA, sticky bottom bar
  - Wire useInstallPrompt hook
  - iOS detection fallback for install instructions
  - Hero image with loading="eager" (LCP optimization)
  - FAQ section renders both visible accordion AND FAQ JSON-LD structured data
  - Edge case: already-installed detection → swap install CTA for deep link
Step 6: Auth screens (src/routes/_auth/) — if Make has auth screens (DangNhap, DangNhapEmail, QuenMatKhau), COPY them directly and apply targeted edits (swap mock auth → real Supabase Auth). Otherwise build from northstar §9.

Building the landing page first validates Make's components + Tailwind config on a real screen before feature work begins.

If EDS §6 lists animation dependencies (motion, react-countup), verify they are installed.
Signal completion when feat(foundation): shared components + landing page + auth screens complete is committed.
```

## Dispatch — Mobile Foundation (mode ≠ pwa only)

**GetViews.vn:** Skip — no `mobile/` app. For upstream RAD only: after Backend and Web Frontend Foundation commit, if deployment mode is `native` or `pwa-then-native`, launch Mobile Developer subagent:

```
Task: Foundation — Mobile App Setup

Read:
- .cursor/agents/mobile-developer.md (your full instructions)
- .cursor/rules/mobile.mdc (prohibitions + NativeWind rules — read FIRST)
- .cursor/rules/copy-rules.mdc (copy quality test)
- agent-workspace/ACTIVE_CONTEXT.md
- artifacts/docs/emotional-design-system.md — §5 Visual Direction (brand colors)
- artifacts/docs/northstar-[app].html — §9 Auth Model, §7c Deployment Mode
- artifacts/docs/screen-specs-[app]-v1.md — Mobile Navigation metadata for tab structure

Mode: Foundation
Follow Foundation Mode in your agent file (Steps 0–6):
  Step 0: Install react-native-reusables
  Step 1: Configure NativeWind (verify tailwind.config.js + global.css + nativewind-env.d.ts + babel.config.js)
  Step 2: Root layout with full provider tree
  Step 3: Tab layout per screen specs
  Step 4: Auth screens per northstar §9
  Step 5: Push notification setup (if §7c specifies push)
  Step 6: First dev build — verify app launches

Signal completion when feat(foundation): mobile app setup complete is committed.
```

## After completion

1. Update `artifacts/plans/project-plan.md` — mark Foundation complete with commit hashes
2. Update `agent-workspace/ACTIVE_CONTEXT.md` — foundation complete, ready for Wave 1
3. Verify landing page is deployed to staging URL — quick visual check that hero, CTA, and install prompt work
4. If mobile: verify dev build launches on simulator/emulator
5. Present to human: "Foundation complete. Landing page live at staging URL. [Mobile app running on simulator.] Ready to begin feature workstreams. Run `/feature [name]` for each Wave 1 feature."

Wave 1 features are listed in `artifacts/plans/build-plan.md`.
