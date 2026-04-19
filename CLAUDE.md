# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**GetViews.vn** — Vietnamese TikTok creative intelligence platform. Users paste a TikTok URL or ask a question in Vietnamese; the system analyzes the video frame-by-frame with Gemini vision, compares it against a pre-indexed corpus of ~46,000 Vietnamese TikTok videos, and returns diagnosis + hook rankings + actionable fixes in Vietnamese via streamed SSE.

**Deployment mode:** `pwa` (web-only). The repo also contains `mobile/` (Expo) + `shared/` scaffolding from the RAD template, but they are out of scope for this app.

**Primary language for user-facing copy: Vietnamese.** No English strings in UI.

## Commands

```bash
npm run dev          # React Router v7 dev server (http://localhost:5173)
npm run build        # Production build → build/client + build/server
npm run preview      # Serve the built client (npx serve build/client)
npm run typecheck    # react-router typegen && tsc --build --force
npm run test         # vitest run (unit tests next to code, jsdom env)
npx vitest run path/to/file.test.ts      # run a single vitest file
npx vitest run -t "test name"            # filter by test name
```

**Vercel install flag (mandatory):** `npm install --legacy-peer-deps`. Locally this also matters whenever React 19 / RR v7 peer ranges conflict — `vercel.json` hard-codes it.

**Playwright (live-site quick-action audit):**

```bash
npx playwright install chromium
npx playwright test auth.setup.ts --headed --project=setup    # one-time login → .auth/user.json
npx playwright test --project=quick-actions                   # default: baseURL = https://getviews.vn
GV_BASE_URL=https://preview-xxx.vercel.app npx playwright test --project=quick-actions
```

Playwright is excluded from vitest (`vitest.config.mts` excludes `tests/**`). Treat `tests/` as live-site audits, `src/**/*.test.ts[x]` as unit tests.

**Cloud Run Python pipeline (under `cloud-run/`):**

```bash
cd cloud-run && uv pip install -e ".[dev]"    # or pip install -e ".[dev]"
pytest                                         # tests in cloud-run/tests/
ruff check                                     # lint (line-length 100, py311)
GCP_PROJECT_ID=... ./deploy.sh                 # build + deploy to Cloud Run (asia-southeast1)
```

**Supabase Edge Functions:** Deno modules in `supabase/functions/`. Deploy via `supabase functions deploy [name]`. Migrations in `supabase/migrations/` — both Supabase MCP (remote apply) and local SQL file must be written; they must never drift. Regen types with `supabase gen types typescript --project-id <ref> > src/lib/database.types.ts` after schema changes.

## Architecture (three-surface split)

This is not a single-codebase app. AI inference is split across three runtimes for latency and cost reasons — **understand which surface a feature belongs to before editing.**

1. **React SPA (this repo root)** — Vite + React Router v7 in SPA mode (`ssr: false`). Only `/` is prerendered for SEO; everything else is client-rendered behind an auth guard. Hosted on Vercel. Source of truth for all UI.

2. **Vercel Edge Functions (`api/`)** — `/api/chat` (text intents ⑤⑥⑦ + follow-ups). Streams Gemini SSE. Auth = user's Supabase JWT in `Authorization: Bearer`. Used for the fast/cheap path.

3. **Cloud Run Python service (`cloud-run/`)** — FastAPI + `google-genai`. Owns video intents ①③④ and batch corpus ingest. SSE `/stream` endpoint called directly from the browser; JWT validated via Supabase JWKS (asymmetric, stateless). Two deployment shapes: user-facing (`min-instances: 1`) and batch (cron-triggered, `min-instances: 0`). This is required because Vercel's 60s timeout cannot complete a video analysis.

4. **Supabase** — DB + Auth + RLS + Storage + Edge Functions (Deno). **RLS is the only authorization boundary** — every table has RLS; JWT in the Supabase client scopes every query. Edge Functions (`supabase/functions/`) handle webhooks (PayOS), cron (expiry, free-query reset, prune, stale processing guard), and Resend email. No custom Node backend exists.

### Intent routing

`src/routes/_app/intent-router.ts` (frontend tier-1 router) decides per user message whether to hit `/api/chat` (Vercel Edge) or the Cloud Run SSE endpoint. URL/handle = structural (high confidence) → Cloud Run or `/app/channel` shortcut; explicit keyword → specialized pipeline; everything else → `follow_up` (free) on Vercel Edge. Don't reinvent routing inside screens — extend `detectIntent` + its tests (`intent-router.test.ts`).

### Data flow / state

- TanStack React Query = **all** server state. `useState` = local UI only. React Context = low-frequency shared state (auth). **No Zustand/Redux/Jotai.**
- Query hooks live in `src/hooks/use*.ts` using keys from `src/lib/query-keys.ts`.
- Supabase client is a **single instance** in `src/lib/supabase.ts`, built from `env` in `src/lib/env.ts` (Zod-validated at import). Never import `@supabase/supabase-js` directly from routes/components/Edge Functions outside this file.
- Typed entity interfaces: `src/lib/api-types.ts` (hand-written) + `src/lib/database.types.ts` (generated). api-types re-exports / extends generated.

### Auth

- Supabase Auth only. `AuthProvider` (`src/lib/auth.tsx`) wraps the app in `src/root.tsx`; `useAuth()` exposes `user`, `session`, `loading`. Provider subscribes to `onAuthStateChange` for refresh/sign-out.
- Auth guard = layout route `src/routes/_app/layout.tsx`. OAuth callback = `src/routes/_auth/callback/route.tsx`.
- **Facebook OAuth is non-negotiable for the Vietnamese market** — don't remove it.

### LLM boundary

- All AI API keys are **server-only**. `GEMINI_API_KEY` lives in Cloud Run env + Vercel Edge env. **Never** `VITE_`-prefix an LLM key — it would ship in the client bundle.
- Components and hooks never call Gemini directly. They go through Supabase Edge Functions, `/api/chat` (Vercel Edge), or Cloud Run SSE.
- Frontend AI wrappers live in `src/lib/` (e.g. `src/lib/niche-resolver.ts`).
- Models: **Gemini 3.x only.** Never reference Gemini 2.5 (EOL June 2026) or 2.0 (EOL March 2026) — `flash-lite-preview` for extraction/classification, `flash-preview` for Vietnamese synthesis. Cost ceiling ~$70/mo across all Gemini usage.

### Critical invariants (TD-1 through TD-5)

When touching billing, payments, or streaming, preserve these — they are the documented tech-debt guards:

- **TD-1 — Atomic credit deduction:** use the Supabase RPC `decrement_credit()` which has a `WHERE credits > 0` guard. Never deduct via two-step read-then-write from the client.
- **TD-2 — PayOS webhook idempotency:** `processed_webhook_events` UNIQUE constraint. Check before writes; retries must be safe.
- **TD-3 — Concurrent request guard:** `profiles.is_processing` boolean. Cron (`cron-reset-processing`) clears flags older than 5 min.
- **TD-4 — SSE reconnection:** Cloud Run emits `stream_id` + `seq` per token and replays from a 60s in-memory buffer on reconnect.
- **TD-5 — Credits granted upfront at PAID webhook.** PayOS is **one-time**, not a subscription. There is no monthly top-up cron.

Other hard rules: `video_corpus` INSERT is batch-only via service_role (client writes blocked by RLS); `chat_messages` are immutable (no UPDATE); soft-delete removed — sessions are hard-deleted via RPC (see migrations `_034`, `_035`, `_036`).

### Route structure

`src/routes.ts` declares the routes explicitly (not pure file-based). Landing at `/` (prerendered), `/login`, `/signup`, `/auth/callback`, then `layout("routes/_app/layout.tsx", …)` guards all `/app/*` routes: `chat`, `onboarding`, `history`, `trends`, `video`, `channel`, `script`, `kol`, `settings`, `learn-more`, `pricing`, `checkout`, `payment-success`.

Every `/app/*` leaf route **must** be code-split with `React.lazy` + `Suspense` in its `route.tsx`; the real screen lives alongside (e.g. `ChatScreen.tsx`). Keep the landing page, auth routes, and layout modules eager — they run on every navigation.

Do **not** use React Router v7 `clientLoader` for data. TanStack Query is the single source of truth.

## Design system

- Visual source of truth: the tracked Studio UIUX pack at `artifacts/uiux-reference/` (`shell.jsx`, `screens/*.jsx`, `styles.css`, `data.js`). Build screens by **copy-then-edit** — never rewrite from memory. Optional gitignored legacy dump may appear at `src/make-import/`.
- `src/components/ui/` **is** the component library (Radix-based, copied from Figma Make). Do not add shadcn/ui, HeroUI, etc. — extend what's there.
- Tokens live in `src/app.css` using Tailwind v4 `@theme inline` syntax with CSS custom properties. Never hardcode hex, px, or raw font sizes — use semantic classes (`bg-primary`, `text-foreground`, `border-default`). `style={{}}` only for genuinely dynamic values.
- Mobile-first: baseline 360–393px, touch targets ≥44×44px, input font ≥16px (prevents iOS zoom). JetBrains Mono for all numerical data (credits, multipliers, corpus sizes). ✕/✓ for diagnosis pass/fail — not emoji.
- Copy rules live in `.cursor/rules/copy-rules.mdc` — forbidden openers (`Chào bạn`, `Tuyệt vời`, `Wow`…) and forbidden words (`bí mật`, `công thức vàng`, `triệu view`, `bùng nổ`…) are enforced. Follow the "state the data → name the finding → give the specific fix" formula.

## Env vars

Copy `.env.example` → `.env.local`. Key distinctions:

- `VITE_*` → ships in client bundle. Only: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_CLOUD_RUN_API_URL`, `VITE_R2_PUBLIC_URL`. All validated in `src/lib/env.ts` — add new client vars to the Zod schema there, never read `import.meta.env` directly.
- Server-only (no `VITE_`): `GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `ENSEMBLEDATA_API_KEY`, `PROXY_URL`, `PAYOS_*`, `RESEND_API_KEY`, `R2_*`.
- Vercel Edge (`api/chat.ts`) reads `SUPABASE_URL` / `SUPABASE_ANON_KEY` with `VITE_*` fallback — set non-`VITE_` aliases in Vercel project settings too.

## Bundle splitting

`vite.config.ts` defines `manualChunks` for `react-vendor`, `react-router`, `@tanstack`, `@supabase`, `@radix-ui`, `lucide-react`, `motion`. Don't remove these without replacing with an equivalent strategy — mobile initial-parse time depends on them. Import icons individually (`import { Camera } from "lucide-react"`), never barrel-imports.

There is a dev-only Vite plugin `vercelEdgeDev` that proxies POST `/api/chat` to `api/chat.ts` via `ssrLoadModule` so the Edge handler works in `npm run dev`. In production, Vercel routes `/api/*` to the Edge Function before the SPA rewrite in `vercel.json`.

## RAD multi-agent workflow

This repo is developed by a multi-agent team orchestrated via Cursor slash commands (`/foundation`, `/feature`, `/deploy`, etc.). See **`AGENTS.md`** for the full team structure, workflow gates, commit conventions, and memory system. Rule authority (highest wins): `.cursor/rules/*.mdc` → `.cursor/agents/*.md` → `.cursor/skills/*.md` → `.cursor/commands/*.md`.

For operational context while working, read:
- `agent-workspace/ACTIVE_CONTEXT.md` — current focus + active workstreams (gitignored)
- `agent-workspace/memory/YYYY-MM-DD.md` — daily append-only log (gitignored)
- `artifacts/docs/tech-spec.md`, `artifacts/plans/build-plan.md`, `artifacts/docs/changelog.md` — tracked specs
- `artifacts/qa-reports/` — per-feature baselines

Commit convention (bisect-friendly, one logical change per commit):
- Phase gates: `feat(foundation): ...`, `feat([feature]): backend complete`, `test([feature]): qa pass`
- Fix loops: `fix(qa): [feature]-ISSUE-NNN — description`

## Out of scope (do not build)

English UI · MCP server access · Reels/Shorts · creator marketplace · video editing · scheduling/posting · Shopee analytics · admin dashboard · recurring subscriptions (PayOS is one-time, packs expire manually) · Zalo notifications (Wave 2) · full livestream analysis (Wave 3+) · OnboardingScreen (niche set inline on first ChatScreen session).
