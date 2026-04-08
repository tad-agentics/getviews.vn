# /native-init

Additive conversion from PWA-only to PWA + Native. Run when starting Phase B of `pwa-then-native` mode. `src/` stays put — nothing moves, everything is copied or extracted.

## Pre-flight checks

- [ ] Mode is `pwa-then-native` (confirmed in northstar §7c)
- [ ] Phase A (PWA) is shipped and running
- [ ] `npm run build` passes
- [ ] Google Play 14-day closed testing started (or starting now with minimal shell)

If any check fails: report to human, do not proceed.

## Step 1: Create workspace structure

```bash
# Add workspaces to root package.json — AFTER create-react-router has already run
# (create-react-router overwrites package.json, so workspaces must be added post-scaffold)
npm pkg set workspaces='["mobile", "shared"]' --json
npm pkg set overrides.react='$react' overrides.react-dom='$react-dom' overrides.react-native='$react-native'

mkdir -p shared/{types,hooks,validation,utils,api}
mkdir -p mobile
```

## Step 2: Extract types first (no dependencies on other shared modules)

```
src/lib/api-types.ts       →  shared/types/api-types.ts
src/lib/database.types.ts  →  shared/types/database.types.ts
src/lib/constants.ts       →  shared/utils/constants.ts  (only if pure — no imports from src/)
```

**Verification:** `grep -r "from.*src/" shared/types/` returns nothing.

## Step 3: Extract validation (depends only on types)

```
src/lib/validation/*.ts    →  shared/validation/
```

Update imports in moved files: `@/lib/api-types` → `../types/api-types`.

**Verification:** `grep -r "from.*src/" shared/validation/` returns nothing.

## Step 4: Extract Supabase factory (depends only on types)

Refactor `src/lib/supabase.ts`:
- Extract `createSupabaseClient` factory → `shared/api/supabase.ts`
- Create `shared/api/supabase-context.ts` (SupabaseProvider + useSupabase hook)
- Keep `src/lib/supabase.ts` as web-specific: calls factory with `localStorage`
- Wrap web root in `<SupabaseProvider value={webClient}>`

**Verification:** `shared/api/supabase.ts` imports only from `../types/`.

## Step 5: Extract utility functions (depends on types, validation)

```
src/lib/formatters.ts      →  shared/utils/formatters.ts    (if pure)
src/lib/[pure-utils].ts    →  shared/utils/
```

**Rule:** Only move a file if ALL its imports resolve within `shared/`. If a util imports a component, hook, or route-specific module — it stays in `src/`.

## Step 6: Extract TanStack Query hooks (depends on types, api, validation)

```
src/hooks/useUser.ts       →  shared/hooks/useUser.ts
src/hooks/useCredits.ts    →  shared/hooks/useCredits.ts
src/hooks/use[Entity].ts   →  shared/hooks/
```

**Rule:** Only extract data-fetching hooks (TanStack Query + Supabase). UI hooks (`useInstallPrompt`, `useLocalStorage`, `useMediaQuery`) stay in `src/hooks/`.

Refactor each hook to use `useSupabase()` from context instead of importing the web-specific client.

**Verification:** `grep -r "from.*src/" shared/hooks/` returns nothing.

## Step 7: Extract color tokens

Create `shared/colors.ts` from EDS §5 brand palette values. See spec §3.4 for format.

## Step 8: Create barrel export

```typescript
// shared/index.ts
export * from "./types/api-types";
export * from "./types/database.types";
export * from "./hooks/useUser";
export * from "./hooks/useCredits";
export * from "./validation";
export * from "./utils";
export * from "./api/supabase";
export * from "./api/supabase-context";
export * from "./colors";
```

Create `shared/package.json`:
```json
{ "name": "shared", "version": "0.0.0", "main": "index.ts", "types": "index.ts" }
```

## Step 9: Update web imports

Replace `@/lib/api-types` → `shared/types/api-types` across all `src/` files.

Add to `vite.config.ts`:
```typescript
resolve: { alias: { "shared": path.resolve(__dirname, "./shared") } }
```

Add to root `tsconfig.json`:
```json
{ "compilerOptions": { "paths": { "shared/*": ["./shared/*"] } } }
```

**Verification:** `npm run build` passes.

## Step 10: Scaffold Expo

```bash
cd mobile && npx create-expo-app . --template blank-typescript
npm install  # installs workspace deps including shared
```

Install all required deps (see spec §11).

Configure NativeWind, EAS, Metro per spec §2-§3.

Create `mobile/tsconfig.json`:
```json
{ "extends": "expo/tsconfig.base", "compilerOptions": { "paths": { "@/*": ["./src/*"], "shared/*": ["../shared/*"] } } }
```

## Step 11: First dev build

```bash
cd mobile && eas build --platform all --profile development
```

## Step 12: Verify

- `npm run build` (web) passes — no broken imports
- `npx expo start --dev-client` (mobile) launches
- `grep -r "from.*src/" shared/` returns nothing
- `grep -r "from.*mobile/" shared/` returns nothing
- `grep -r "from.*mobile/" src/` returns nothing

## After completion

1. Update `agent-workspace/ACTIVE_CONTEXT.md` — Phase B started, workspace structure ready
2. Present to human: "Native workspace scaffolded. Web app unchanged. Ready for mobile foundation — run `/foundation` to set up mobile app shell, then `/feature` for screen translation."
3. Commit: `chore(native-init): workspace structure + shared extraction complete`
