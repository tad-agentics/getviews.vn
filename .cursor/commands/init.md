# /init

First-time project initialization. Run this once when starting a new project from the RAD template, before any phase commands.

## What this does

- Initializes `agent-workspace/` from templates
- Confirms Phase 1 artifacts are in place
- Fills in `copy-rules.mdc` from the EDS
- Scaffolds the React Router v7 (Vite) project structure, installs dependencies, and configures Vitest
- Creates the `staging` branch and links the Vercel project
- Sets the project name in `ACTIVE_CONTEXT.md`
- Reports what's ready and what the next step is

## Steps

### 1. Initialize `agent-workspace/`

Copy templates if not already present:

```bash
cp artifacts/templates/ACTIVE_CONTEXT.md agent-workspace/ACTIVE_CONTEXT.md
cp artifacts/templates/memory-YYYY-MM-DD.md agent-workspace/memory/$(date +%Y-%m-%d).md
```

Open `agent-workspace/ACTIVE_CONTEXT.md` and set:
- `Updated:` to today's date and time
- `Current focus:` to "Init — confirming Phase 1 artifacts, ready for Phase 2"

### 2. Confirm Phase 1 artifacts + structural validation

Phase 1 artifacts are produced externally and validated via `/office-hours`. They must exist before `/init` can proceed.

Check that both required inputs exist in `artifacts/docs/`:

| File | Required? |
|---|---|
| `artifacts/docs/northstar-[app].html` | **Hard stop** — do not proceed if missing |
| `artifacts/docs/emotional-design-system.md` OR `artifacts/docs/eds-[app].html` | **Hard stop** — EDS may be markdown or branded HTML. Accept either format. |
| `.cursor/rules/copy-rules.mdc` | Soft check — if still the placeholder, step 4 fills it from the EDS |

If northstar or EDS are missing: report exactly which files are absent and stop.

**Structural validation (mandatory):** Read the northstar and validate that all 12 required sections are present and substantive. Check for:

| Section | Validation |
|---|---|
| §1 The Problem | Present, written from user perspective |
| §2 Primary User | Named person with age, occupation, friction moment |
| §4 Revenue Model | Specific price point (not "TBD" or a range) |
| §5 Value Proposition | Follows formula: "[App] helps [user] [do X] so that [Y], without [Z]" |
| §6 Competitive Moat | Moat type explicitly named (data/network/switching/distribution/brand) |
| §7 Build Scope | Table covers core loop + retention + monetization + landing page |
| §8 Not Building | Specific feature names, not vague categories |
| §9 Auth Model | Exact method specified, not "TBD" |
| §10 Integrations | Env var names for every service |
| §11 Payment | Provider named with webhook events |
| §12 Feature Grouping | Maps to build waves with dependencies |

If northstar contains §7c (Deployment Mode) and mode ≠ `pwa`:
- Validate mode matches device API requirements
- Validate store accounts enrolled (or enrollment timeline)
- For `pwa-then-native`: validate Phase B trigger is defined

**If 3+ sections are placeholder or missing:** Hard stop. Tell the human to run `/office-hours` first — it will guide them through producing complete Phase 1 artifacts.

**If 1–2 sections are weak but present:** Warn the human with specific gaps. Allow proceeding if human explicitly approves.

### 3. Read Phase 1 artifacts

Read northstar and EDS to extract:
- App name and one-sentence description
- Build scope (feature count from §7)
- Voice register (from EDS)
- Auth method (from §9 — needed for /setup env var guidance)
- Payment provider (from §11 — needed for /setup MCP and dependency decisions)
- External integration env vars (from §10 — needed for .env.example)
- Whether EDS §6 defines dopamine moments requiring motion (needed for Step 6 deps)

### 4. Confirm `copy-rules.mdc` is populated

Read `.cursor/rules/copy-rules.mdc`. If it still contains placeholder content (brackets like `[word]`, `[adjective]`), extract from the EDS and fill in every section:

- **Copy Formula** — extract formula, length limit, structure, tone, person from EDS copy formula section
- **Forbidden Opening Words** — extract from EDS forbidden patterns as comma-separated list
- **Forbidden Words** — extract from EDS forbidden patterns as comma-separated list
- **Screen-Context Copy Rules** (7 contexts) — extract emotional objective, formula override, and one real example per context type from EDS screen-context rules
- **Paywall / Purchase Moment** — extract from EDS paywall copy guidance
- **Forbidden Patterns** — extract named anti-patterns from EDS
- **Copy Quality Test** — extract 5 binary questions from EDS quality test
- **Hard Rules** — set language and market (e.g., "Copy written in Vietnamese for Vietnam B2C")

Every section must contain real, project-specific content. No `[paste from EDS]` placeholders.

### 5. Create React Router v7 app

```bash
npx create-react-router@latest . --yes
```

This scaffolds a React Router v7 project with Vite and TypeScript.

### 5b. Workspace scaffold (mode ≠ pwa only)

If northstar §7c deployment mode is `native` or `pwa-then-native`, add workspace support **after** the React Router scaffold (which overwrites `package.json`):

```bash
npm pkg set workspaces='["mobile", "shared"]' --json
npm pkg set overrides.react='$react' overrides.react-dom='$react-dom' overrides.react-native='$react-native'
```

Add to `vite.config.ts`:
```typescript
resolve: { alias: { "shared": path.resolve(__dirname, "./shared") } }
```

Add to root `tsconfig.json` paths:
```json
"shared/*": ["./shared/*"]
```

Verify `shared/` exists (from template). **GetViews.vn** is web-only — there is no `mobile/` workspace; skip npm `workspaces` linking for native.

For `native` mode, scaffold Expo:
```bash
cd mobile && npx create-expo-app . --template blank-typescript
eas init
```

For `pwa-then-native` mode: skip mobile scaffold now — run `/native-init` after Phase A ships.

### 6. Install dependencies

```bash
npm install @supabase/supabase-js @tanstack/react-query zod
npm install -D vitest @vitejs/plugin-react-swc jsdom @testing-library/react @testing-library/dom vite-tsconfig-paths @tailwindcss/vite
```

**Compiler note:** Default is **`@vitejs/plugin-react-swc`** (faster HMR/builds). If SWC mis-parses a dependency or you need a Babel-only transform, swap to `@vitejs/plugin-react` in `vite.config.ts` and Vitest config — last resort.

If SWC mis-parses a dependency, fall back: `npm install -D @vitejs/plugin-react && npm uninstall @vitejs/plugin-react-swc`, then swap the plugin in `vite.config.ts` and `vitest.config.mts`.

**PWA — evaluate and install one:**
```bash
# Option A (recommended, more battle-tested for Vite):
npm install -D vite-plugin-pwa
# Option B (if Serwist Vite plugin is mature):
npm install -D @serwist/vite serwist
```

Evaluate which PWA plugin is more stable for Vite at the time of build. Configure the chosen plugin in `vite.config.ts` (template already has placeholder comments for both).

**Conditional — if EDS §6 (Dopamine Moments) requires animation:**
```bash
npm install motion react-countup
```
Only install if Step 3 extraction confirmed dopamine moments exist.

### 7. Scaffold project structure

Create the following directories if they don't exist:

- `src/lib/` — `env.ts` (Zod client env), Supabase client, shared utilities
- `src/lib/data/` — typed query functions
- `src/hooks/` — custom hooks (useAuth, useProfile, etc.)
- `src/components/` — shared components
- `src/routes/_index/` — landing page (pre-rendered)
- `src/routes/_auth/` — auth screens
- `src/routes/_app/` — authenticated app screens
- `public/icons/` — PWA icons (192×192 and 512×512, `any` + `maskable` variants)
- `public/screenshots/` — PWA install dialog screenshots
- `public/fonts/` — self-hosted font files (Vietnamese-compatible)
- `supabase/functions/` — Edge Functions
- `supabase/migrations/` — migration files

Verify template infrastructure files are in place:
- `react-router.config.ts` — `ssr: false`, `prerender: ['/']`
- `vite.config.ts` — React Router + Tailwind + PWA plugin (uncomment chosen option)
- `vercel.json` — SPA rewrite rules
- `.cursorignore` — excludes node_modules, dist, .env, database.types.ts
- `.cursorindexingignore` — excludes migrations, seed, templates, memory, database.types.ts

Create `vitest.config.mts` in the project root:

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react-swc'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
  },
})
```

Add scripts to `package.json`:
```json
{
  "scripts": {
    "dev": "react-router dev",
    "build": "react-router build",
    "preview": "npx serve build/client",
    "test": "vitest run"
  }
}
```

Present to human: "Place PWA icons in `public/icons/` (192×192 and 512×512, both regular and maskable). Place a Vietnamese-compatible font file (.woff2) in `public/fonts/` for self-hosting."

### 7b. Set executable permissions on skill scripts

```bash
chmod +x .cursor/skills/*/scripts/*.sh
```

### 8. Set up environment variables

Ensure `src/lib/env.ts` exists and validates every required `VITE_*` key the app reads (minimum: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`). Extend the Zod schema when adding new client env vars — see `backend.mdc` / `frontend.mdc`.

**Fail-fast `env` (read before first `npm run dev` / `npm run build`):** Any import of `@/lib/env` runs Zod validation **immediately** at module load. If `.env.local` is missing, empty, or invalid, **Vite will throw during dev/build startup** and the stack trace often points at `src/lib/env.ts` — that is expected, not a bundler bug. Fill `.env.local` (real URL + publishable key) before starting the dev server so the app can compile.

Copy `.env.example` to `.env.local`. Add env vars from Northstar §10 and §11 to both `.env.example` and `.env.local`:

**Always required:**
```
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
```

**Server-only (Edge Functions only — set via `supabase secrets set` during deploy):**
```
SUPABASE_SERVICE_ROLE_KEY=
OPENROUTER_API_KEY=                  # Required — all RAD apps use LLM via OpenRouter
```

**From Northstar §10 — add if external integrations specified:**
```
# [Integration name from §10]
[VAR_NAME from §10]=
```

**From Northstar §11 — add if payment provider specified:**
```
# [Payment provider from §11]
[VAR_NAMES from §11]=
```

`.env.local` is gitignored. Present the complete `.env.local` to the human to fill in.

### 9. Configure base MCP servers

Create `.cursor/mcp.json` with the base servers every RAD project requires:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase@latest", "--access-token", "<SUPABASE_ACCESS_TOKEN>"]
    },
    "vercel": {
      "command": "npx",
      "args": ["-y", "@vercel/mcp-adapter", "--token", "<VERCEL_TOKEN>"]
    },
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

Present to human: "Fill in credentials in `.cursor/mcp.json`. Context7 requires no credentials. Never commit this file — it is gitignored."

**Do not add Figma MCP by default.** Figma Make outputs code files directly — most builds don't need MCP. If the human uses Figma Dev Mode and wants MCP file delivery for native builds (optional convenience — saves manual file copying), add at their request:
```json
"figma": { "url": "https://mcp.figma.com/mcp" }
```

### 10. Create staging branch

```bash
git add -A
git commit -m "chore(init): project scaffold and workspace initialized"
git checkout -b staging
git push -u origin staging
```

### 11. Link Vercel project

```bash
npx vercel link
```

Follow prompts to link this repo to Vercel. Every `git push origin staging` triggers a preview deploy.

### 12. Update `agent-workspace/ACTIVE_CONTEXT.md`

- `Updated:` — today's date and time
- `Current focus:` — "Init complete — ready for Phase 2 (screen specs + Figma Make)"
- `Next up:` — "/phase2 — dispatch Product Designer for screen specs and Figma Make brief"

### 13. Report to human

```
## Project initialized: [App Name]

Phase 1 artifacts confirmed:
  ✓ northstar-[app].html
  ✓ emotional-design-system.md (or eds-[app].html)
  ✓ copy-rules.mdc

React Router v7 (Vite) scaffold: ✓
Base packages: @supabase/supabase-js, zod
PWA: [vite-plugin-pwa or @serwist/vite] configured
Test runner: vitest (npm test = vitest run)
.env.local created — fill in Supabase credentials + integration vars before proceeding
MCP config created — fill in Supabase + Vercel credentials in .cursor/mcp.json
Staging branch: created and pushed to origin/staging
Vercel: linked — push to staging to get a preview URL

Action required from human:
  - Fill in .env.local credentials (required before `npm run dev` — `src/lib/env.ts` throws at import time if URL/key missing; stack may point at env.ts)
  - Fill in .cursor/mcp.json tokens (Supabase, Vercel)
  - Place PWA icons in public/icons/ (192×192 + 512×512, regular + maskable)
  - Place Vietnamese font file (.woff2) in public/fonts/

Build scope: [N] features + 1 landing page
Voice register: [from EDS]

Ready for Phase 2. Run /phase2 to dispatch the Product Designer.
```
