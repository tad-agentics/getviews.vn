# GetViews.vn

Web app (PWA) for Vietnamese TikTok creative intelligence — React Router v7, Supabase, TanStack Query, Vercel, Cloud Run Python pipeline.

## Repo map

| Path | Purpose |
|------|---------|
| `src/` | SPA: routes, hooks, UI (`src/components/ui/` = shared primitives) |
| `api/` | Vercel Edge handlers (`/api/chat`, `/api/landing-stats`, …) |
| `supabase/` | Migrations, Edge Functions (Deno), seed |
| `cloud-run/` | FastAPI pipeline (video intents, batch jobs) |
| `shared/` | Cross-surface types/helpers |
| `artifacts/` | Specs, runbooks, QA baselines — **not** bundled at runtime |
| `tests/` | Playwright live-site audits (excluded from Vitest) |
| `.cursor/` | Cursor rules, commands, agent/skills metadata |

Canonical engineering notes: **`CLAUDE.md`** (stack, invariants, env). Multi-agent workflow reference: **`AGENTS.md`**.

## Prerequisites

- Node 20+ (match Vercel / team standard)
- `npm install --legacy-peer-deps` (required for this repo’s peer ranges; same as Vercel)

## Commands

```bash
npm run dev          # local dev (http://localhost:5173)
npm run build        # production client build
npm run typecheck    # typegen + tsc + design-token guard
npm run test         # Vitest (unit tests under src/)
npm run verify       # typecheck + test (same as CI)
npm run knip         # unused files / exports (run periodically; see Housekeeping)
```

**Python pipeline** (Cloud Run): see `cloud-run/README.md` or `CLAUDE.md` § Cloud Run.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs `npm run verify` on push and pull requests to `main`.

## Housekeeping

- Run **`npm run knip`** occasionally to find unused files and exports; fix in small PRs (Knip may exit non-zero until findings are cleared).
- Move **superseded** long-form docs to `artifacts/docs/archive/` with a short note at the top of the moved file.
- Keep **`agent-workspace/`** for local session notes (gitignored); do not commit scratch state.

## License / product

Proprietary — GetViews.vn.
