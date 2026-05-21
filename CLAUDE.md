# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**GetViews.vn** — Vietnamese TikTok creative intelligence platform. Users paste a TikTok URL or ask a question in Vietnamese; the system analyzes the video frame-by-frame with Gemini vision, compares it against a corpus of Vietnamese TikTok videos (built up via nightly EnsembleData ingest), and returns diagnosis + hook rankings + actionable fixes in Vietnamese via streamed SSE.

**Status: pre-launch.** The corpus is still growing — at any point, expect that some niches have thin samples and per-niche benchmarks may sit on the "thin/unreliable" claim tier until the nightly cron has run long enough to build coverage. **Do not put fabricated corpus-size numbers in user-facing copy or docs**; query `video_corpus` for actual counts when a number matters.

**Deployment mode:** `pwa` (web-only). The `mobile/` Expo workspace was removed; this app ships web only. `shared/` remains for cross-surface types/API helpers used by the web app.

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

Corpus nightly ingest **selection criteria** (instructiveness rank, purity gates): [`artifacts/docs/corpus-ingest-criteria-v1.md`](artifacts/docs/corpus-ingest-criteria-v1.md) · architecture §12.1 in [`system-design.md`](artifacts/docs/system-design.md).

```bash
cd cloud-run && uv pip install -e ".[dev]"    # or pip install -e ".[dev]"
pytest                                         # tests in cloud-run/tests/
ruff check                                     # lint (line-length 100, py311)
GCP_PROJECT_ID=... ./deploy.sh                 # build + deploy to Cloud Run (asia-southeast1)
```

**Supabase Edge Functions:** Deno modules in `supabase/functions/`. Deploy via `supabase functions deploy [name]`. Migrations in `supabase/migrations/` — both Supabase MCP (remote apply) and local SQL file must be written; they must never drift. Regen types with `supabase gen types typescript --project-id <ref> > src/lib/database.types.ts` after schema changes.

## Architecture

> Full system design, component map, data flows, caching, billing, background jobs, and critical invariants:
> **`artifacts/docs/system-design.md`** — the single source of truth. Update it in the same commit as any architectural change.

Quick reference for AI operating constraints:

- **Three runtimes:** React SPA (Vercel) · Vercel Edge (`api/`) · Cloud Run Python (`cloud-run/`). Understand which surface owns a feature before editing.
- **Gemini API keys are server-only.** `VITE_` prefix on a Gemini key ships it to the client bundle — forbidden.
- **RLS is the only auth boundary** for DB access. No middleware layer.
- **TanStack Query = all server state.** `useState` = local UI. No Zustand/Redux/Jotai.
- **Supabase client is a single instance** (`src/lib/supabase.ts`). Never import `@supabase/supabase-js` elsewhere.
- **`video_corpus` INSERT is batch-only** (service role). `chat_messages` are immutable (no UPDATE).
- **Two parallel session models — both live:** Chat model (`chat_sessions` + `chat_messages`) handles text intents ⑤⑥⑦ and is still actively written by Cloud Run `intent.py`. Answer sessions model (`answer_sessions` + `answer_turns`) handles structured video/channel diagnosis (Intents ①③④). Do NOT delete either. `history_union` RPC surfaces both in the history drawer.
- **Gemini 3.x only.** `gemini-3.1-flash-lite` (GA stable, $0.25/$1.50 per 1M) is the universal default — extraction, classification, synthesis, intent. **Cost ceiling ~$80–90/mo** across Gemini + optional **HI-14** GCP Speech-to-Text (`vi-VN` on **video** paths only; carousels skip STT). Optional **HI-13** Batch API discount on nightly video shards offsets part of ASR add when enabled.
- **Facebook OAuth is non-negotiable** for the Vietnamese market.
- **Intent routing:** extend `detectIntent()` in `src/routes/_app/intent-router.ts` — never reinvent routing inside screens.
- **Channel diagnosis (`POST /channel/diagnose`, Cloud Run):** corpus-first peers + two-axis persona + deterministic `score_card` / hashtag / next-video templates; SSE `score_card` event; `channel_diagnoses` v2 JSONB columns; cache replay must re-emit all v2 fields. See `system-design.md` §16.
- **Every `/app/*` leaf route** must be code-split with `React.lazy` + `Suspense`. Do not use `clientLoader`.
- **Critical invariants TD-1–TD-7** (credit deduction, webhook idempotency, processing guard, SSE reconnection, upfront credits, junction parity for `route`, live/batch extraction parity) — see `system-design.md` §10.

### Niche model (two-axis; batch routing HI-11)

- **Axes:** `creator_niches` (16 UX buckets) and `content_classifications` (74) linked by `creator_niche_content_classes` (M:N, `is_primary`).
- **Legacy bridge:** `video_corpus.niche_id` remains for corpus filtering; Python `legacy_niche_id_for_creator_niche()` and TypeScript `legacyNicheIdForCreatorNiche()` **must stay identical**.
- **Batch ingest resolver:** `NICHE_RESOLVER_MODE` = `shadow` (default) or `route`. In **shadow**, hashtag + ladder stay canonical for `niche_id` / `content_class_id`; `niche_resolution_source`, `niche_resolution_confidence`, and `inferred_creator_niche_id` capture Gemini two-axis telemetry. In **route**, high-confidence HI-9 output + junction can override niche and set `content_class_id`. **Production:** shadow observation → 100-row audit → flip → MV refresh (see `artifacts/docs/two-axis-niche-cutover-runbook.md` Part B — plan “Phase 7”).
- **Provenance:** Shadow and route paths populate `niche_resolution_source` etc.; ME-17 backfill targets rows with `niche_resolution_source IS NULL` after flip.

## Design system

- Visual source of truth: the tracked Studio UIUX pack at `artifacts/uiux-reference/` (`shell.jsx`, `screens/*.jsx`, `styles.css`, `data.js`). Build screens by **copy-then-edit** — never rewrite from memory. Optional gitignored legacy dump may appear at `src/make-import/`.
- `src/components/ui/` **is** the component library (Radix-based, copied from Figma Make). Do not add shadcn/ui, HeroUI, etc. — extend what's there.
- Tokens live in `src/app.css` using Tailwind v4 `@theme inline` syntax with CSS custom properties. Never hardcode hex, px, or raw font sizes — use semantic classes (`bg-primary`, `text-foreground`, `border-default`). `style={{}}` only for genuinely dynamic values.
- Mobile-first: baseline 360–393px, touch targets ≥44×44px, input font ≥16px (prevents iOS zoom). JetBrains Mono for all numerical data (credits, multipliers, corpus sizes). ✕/✓ for diagnosis pass/fail — not emoji.
- **Responsive breakpoint hierarchy** (mix of Tailwind defaults + `min-[NNNpx]` arbitrary breakpoints):
  - **360–393px** — mobile baseline. Single column, ≥44px touch targets, ≥16px inputs, `safe-area-inset` for notch.
  - **`sm:` (640px)** — Tailwind default. Used by landing-page grids that step from 3→4 cols.
  - **`min-[700px]:`, `min-[820px]:`** — Answer-session bodies (Pattern/Lifecycle cell grids, Timing heatmap) use these for "comfortable two-column".
  - **`md:` (768px)** — Tailwind default. Landing-page step from 4→5 cols.
  - **`min-[900px]:`, `min-[1100px]:`** — Studio Home → wider sidebars + multi-pane layouts.
  - **`lg:` (1024px)** — desktop sidebar appears (mobile sidebar drawer hides), bottom-tab-bar hides.
  Stay inside this hierarchy for new screens; don't introduce one-off breakpoints unless the design genuinely needs them.
- Copy rules live in `.cursor/rules/copy-rules.mdc` — forbidden openers (`Chào bạn`, `Tuyệt vời`, `Wow`…) and forbidden words (`bí mật`, `công thức vàng`, `triệu view`, `bùng nổ`…) are enforced. Follow the "state the data → name the finding → give the specific fix" formula.

## Env vars

Copy `.env.example` → `.env.local`. Key distinctions:

- `VITE_*` → ships in client bundle. Only: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`, `VITE_CLOUD_RUN_API_URL` (user pod), `VITE_CLOUD_RUN_BATCH_URL` (batch pod — required for `/admin/*`; soft-falls-back to the user URL for dev / single-service "all" deployments), `VITE_R2_PUBLIC_URL`, `VITE_ZALOPAY_ENABLED`. All validated in `src/lib/env.ts` — add new client vars to the Zod schema there, never read `import.meta.env` directly.
- Server-only (no `VITE_`): `GEMINI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `ENSEMBLEDATA_API_KEY`, `PROXY_URL`, `BATCH_SECRET`, `BATCH_SERVICE_BASE_URL` (set on the user pod so its `batch_proxy` can forward to batch), `PAYOS_*`, `RESEND_API_KEY`, `R2_*`.
- Vercel Edge (`api/chat.ts`) reads `SUPABASE_URL` / `SUPABASE_ANON_KEY` with `VITE_*` fallback — set non-`VITE_` aliases in Vercel project settings too.
- Supabase Vault holds `cloud_run_api_url` (must point to the **batch** service URL — pg_cron schedules call `/batch/*` paths) and `cloud_run_batch_secret` (must match `BATCH_SECRET` on the batch pod). Rotating either without updating the other breaks every cron silently — `cron.job_run_details.return_message` will succeed but `net._http_response.status_code` will be 401/404. **Verify** with `vault.decrypted_secrets` (preview the URL hostname) and `POST /batch/ping` on the batch service. Mitigations: admin rule `pg_net_batch_http_4xx` (RPC `admin_pg_net_batch_http_4xx_events`) and hourly pg_cron `cron-pg-net-batch-http-4xx-watch` — see migration `20260704000000_pg_net_batch_http_4xx_audit.sql`.

## Bundle splitting

`vite.config.ts` defines `manualChunks` for `react-vendor`, `react-router`, `@tanstack`, `@supabase`, `@radix-ui`, `lucide-react`, `motion`. Don't remove these without replacing with an equivalent strategy — they keep first-load chunks bounded. Import icons individually (`import { Camera } from "lucide-react"`), never barrel-imports.

There is a dev-only Vite plugin `vercelEdgeDev` that proxies POST `/api/chat` to `api/chat.ts` via `ssrLoadModule` so the Edge handler works in `npm run dev`. In production, Vercel routes `/api/*` to the Edge Function before the SPA rewrite in `vercel.json`.

## RAD multi-agent workflow

This repo is developed by a multi-agent team orchestrated via Cursor slash commands (`/foundation`, `/feature`, `/deploy`, etc.). See **`AGENTS.md`** for the full team structure, workflow gates, commit conventions, and memory system. Rule authority (highest wins): `.cursor/rules/*.mdc` → `.cursor/agents/*.md` → `.cursor/skills/*.md` → `.cursor/commands/*.md`.

For operational context while working, read:
- `agent-workspace/ACTIVE_CONTEXT.md` — current focus + active workstreams (gitignored)
- `agent-workspace/memory/YYYY-MM-DD.md` — daily append-only log (gitignored)
- `artifacts/docs/system-design.md` — architecture, flows, invariants (primary reference)
- `artifacts/plans/build-plan.md`, `artifacts/docs/changelog.md` — feature tracker + deviations
- `artifacts/qa-reports/` — per-feature baselines

Commit convention (bisect-friendly, one logical change per commit):
- Phase gates: `feat(foundation): ...`, `feat([feature]): backend complete`, `test([feature]): qa pass`
- Fix loops: `fix(qa): [feature]-ISSUE-NNN — description`

## Out of scope (do not build)

English UI · MCP server access · Reels/Shorts · creator marketplace · video editing · scheduling/posting · Shopee analytics · recurring subscriptions (PayOS is one-time, packs expire manually) · Zalo notifications (Wave 2) · full livestream analysis (Wave 3+).
