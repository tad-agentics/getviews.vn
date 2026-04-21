---
status: revised after re-verification
owner: codebase health
last_updated: 2026-04-21
verified_against:
  - "rg across the entire repo (not just src/)"
  - "ts-prune -p tsconfig.app.json (latest run)"
  - "ruff F401/F841 over cloud-run/getviews_pipeline + main.py"
  - "Phase C.7 closure audit (artifacts/qa-reports/phase-c-design-audit-chat-deletion.md)"
  - "tech-spec.md and screen-specs-getviews-vn-v1.md"
inputs_discarded:
  - "knip with no config — produced too many false positives to act on"
out_of_scope:
  - "src/make-import/** — excluded from tsconfig.app.json"
  - "mobile/** — separate Expo app"
  - "supabase/functions/** — Deno edge runtime"
  - "artifacts/uiux-reference/** — design reference"
---

# Dead-code removal plan (verified)

## What changed vs the first draft

The first draft had three wrong calls; this revision corrects them:

1. **`CreditBar`, `URLChip`, `StreamingStatusText`, `FreeQueryPill`,
   `AnalysisLimitCard` were *not* "obvious orphans"** — they are
   chat-surface widgets that lost their consumer when **Phase C.7
   deleted `ChatScreen.tsx`** (`artifacts/qa-reports/phase-c-design-audit-chat-deletion.md`).
   The spec docs (`tech-spec.md`, `screen-specs-getviews-vn-v1.md`) still
   reference them. They are deletable **only after a product
   confirmation that chat will not return**, plus a spec amendment.
2. **`AgentStepLogger` + `StepSpinner` + `StepThumbnails` were *not*
   "obvious orphans"** — they are the P0-6 step-event UI; `useSessionStream`
   already collects `StepEvent[]` from the SSE stream, and
   `output-quality-plan.md` describes wiring them via a not-yet-built
   `MessageRenderer`/`stream-handler`. Either ship the wiring or remove
   the whole pipe (UI + `stepEvents` state).
3. **`useInstallPrompt` was *not* "PWA — keep if active"** — it is
   mandated by `tech-spec.md` §18 and `foundation.md` says to wire it
   into landing CTAs. The wiring is the missing piece; the hook is
   fine to keep.

The mechanical wins (`ruff` and unused npm deps) all re-verified.

## Summary of what is confirmed dead

```
B1  cloud-run            14 × F401  + 1 × F841                         (ruff --fix + 1 manual)
B2  npm deps             @anthropic-ai/sdk, @payos/node                (rg: 0 hits in code)
B3  src/lib/batch/**     classifiers.ts + quality-gates.ts             (whole dir; Python does the work)
B3  src/lib/constants.ts unused barrel                                 (no importer in src/)
B3  src/components/ui/Card.tsx                                         (superseded by v2/Card.tsx)
B3  src/components/v2/index.ts + Composer.tsx                          (barrel + composer with no callers)
B4  small unused exports inside otherwise-live files                   (table below)
```

Everything else needs **a product call first** (see "Tier 2 — needs
product decision"). Do not delete on tooling output alone.

## Removal rules (non-negotiable)

1. **Verify with `rg <symbol>` across the whole repo** (not just `src/`)
   immediately before deletion. Spec docs in `artifacts/` count as a
   signal that someone *meant* to use it.
2. **Never delete**:
   - `default` exports of `route.tsx` files (RR file routing).
   - `loader` / `action` / `meta` exports.
   - Token / event types in `src/lib/types/sse-events.ts` — wire format.
   - Anything inside `supabase/functions/`, `cloud-run/`, `mobile/`, or
     `src/make-import/` based on the web app graph alone.
   - `useChatSessions`, `useSearchSessions` — Phase C.7 closure
     **explicitly** kept these alive for `/history` (chat-legacy read).
3. One concern per commit. Do not mix tooling-config edits with deletions.
4. Each batch ends with: `npm run typecheck`, `npm test`, and (if Cloud
   Run is touched) `cd cloud-run && python3 -m ruff check && pytest`.

---

## Tier 1 — mechanical (open one PR, two commits)

### B1 — Cloud Run `ruff` cleanup

Re-verified just now: `python3 -m ruff check getviews_pipeline main.py
--select F401,F841 --statistics` reports **14 × F401 + 1 × F841**.

```bash
cd cloud-run
python3 -m ruff check getviews_pipeline main.py --select F401,F841 --fix
# F401 (unused imports): all 14 auto-fixed.
# F841 (unused variable in report_pattern_compute.py): inspect, drop the
# assignment, keep the surrounding compute. --unsafe-fixes is fine here.
python3 -m ruff check getviews_pipeline main.py --select F401,F841   # expect: All checks passed
pytest
```

**Commit:** `cloud-run: drop unused imports + unused pct_sound binding`

### B2 — Drop unused npm dependencies

Re-verified — both packages have **zero** import sites in the runtime
code (only `package*.json`, docs, and the rule that forbids the SDK):

| Package | Why it's unused |
|---|---|
| `@anthropic-ai/sdk` | `.cursor/rules/backend.mdc:301` explicitly forbids any LLM SDK; OpenRouter is called via `fetch`. No `import` anywhere in `src/`, `api/`, `app/`, `shared/`, `supabase/`, `cloud-run/`. |
| `@payos/node` | PayOS is called via `fetch` in `supabase/functions/create-payment` and `supabase/functions/payos-webhook` (Deno runtime — can't use the Node SDK anyway). No `import` anywhere. |

```bash
npm uninstall @anthropic-ai/sdk @payos/node
npm run typecheck && npm test
```

**Commit:** `deps: remove unused @anthropic-ai/sdk and @payos/node`

> Leave **all `@radix-ui/*`** alone — they back `src/components/ui/*`
> shadcn primitives, which are imported across many screens.

---

## Tier 2 — needs a product decision (do not delete on tooling alone)

### Chat-surface widgets (Phase C.7 collateral)

Phase C.7 deleted `ChatScreen.tsx` but **left the bottom-of-screen
widgets behind**. They have zero importers in `src/`, but the spec docs
(`tech-spec.md` FR-15/16/25, `screen-specs-getviews-vn-v1.md`) still
treat them as required UI:

```
src/routes/_app/components/AnalysisLimitCard.tsx
src/routes/_app/components/CreditBar.tsx
src/routes/_app/components/FreeQueryPill.tsx
src/routes/_app/components/StreamingStatusText.tsx
src/routes/_app/components/URLChip.tsx
```

**Decision needed:** is the chat surface coming back, or are these
widgets going to be re-targeted to `/answer`?

- If **chat is permanently dead** → delete all 5 files **and** open a
  spec amendment PR that strikes FR-15/16/25 + the related screen-spec
  paragraphs. Don't leave the spec stale.
- If **CreditBar et al. should appear on `/answer`** → leave them and
  add tickets to wire them into the answer surface. Either way, do
  **not** silently drop them.

### Step-event UI (P0-6, half-wired)

```
src/components/chat/AgentStepLogger.tsx
src/components/chat/StepSpinner.tsx
src/components/chat/StepThumbnails.tsx
```

Plumbing is already shipped: `useSessionStream` parses
`{ step?: StepEvent }` SSE tokens and exposes `stepEvents: StepEvent[]`
in returned state (lines 67, 506). Cloud Run emits the events. **No UI
consumes the array** — `output-quality-plan.md` describes the missing
`MessageRenderer.tsx` + `stream-handler.ts` glue.

**Decision needed:** ship the wiring or remove the pipe.

- If **ship** → build `MessageRenderer` per `output-quality-plan.md`
  step 6, render `<AgentStepLogger events={stepEvents} />` from the
  `/answer` shell.
- If **remove** → delete the three files, delete the `stepEvents`
  field + reducer cases in `useSessionStream.ts`, and either delete
  the `StepEvent` type or mark the file as wire-format-only.

### `useInstallPrompt` (PWA install banner)

`src/hooks/useInstallPrompt.ts` is **mandated by `tech-spec.md` §18**
and the foundation playbook says to wire it into landing-page CTAs.
Currently no caller — that's the bug, not the hook.

**Action:** keep the hook. Open a small ticket to wire it on the
landing-page install CTA. Do not delete.

### `resolveDestination` (C.7 routing matrix)

`src/routes/_app/intent-router.ts:77` — `phase-c-design-audit-chat-deletion.md`
claims tests cover it, but `intent-router.test.ts` only imports
`appendTurnKindForQuery`, `detectIntent`, `planAnswerEntry`. The audit
doc is wrong; the function is genuinely uncalled.

**Action:** **add the test** the audit doc claimed exists — one
parameterised case per `INTENT_DESTINATIONS` entry plus the dynamic
`follow_up_classifiable` branches. Then the function is genuinely
covered and stays. This is cheaper than deleting + re-adding when
Phase D needs it.

---

## Tier 3 — true orphan files (whole-file deletes, low risk)

Each file below has **zero importers anywhere in the repo** (verified
with `rg from ['\"]<path>` and `rg <SymbolName>`).

### Whole-file deletes

| File | Evidence |
|---|---|
| `src/lib/constants.ts` | `rg "@/lib/constants"` → 0 hits. Exports `APP_NAME`, `APP_TAGLINE`, `CREDIT_PACKS`, `TIERS`, `NICHE_IDS`, etc. — all duplicated by `cloud-run` constants or pulled from DB. |
| `src/lib/batch/classifiers.ts` | `rg "@/lib/batch"` → 0 hits. `classifyCreatorTier`, `getVietnamHour` are also implemented in `cloud-run/getviews_pipeline/claim_tiers.py` (used). |
| `src/lib/batch/quality-gates.ts` | Same; `validateForCorpus` has a Python equivalent in the pipeline. |
| `src/components/ui/Card.tsx` | `rg "@/components/ui/Card"` → 0 hits. Different file from `src/components/v2/Card.tsx` (which **is** used by `PulseCard.tsx`). |
| `src/components/v2/Composer.tsx` | Only consumer is `src/components/v2/index.ts` (barrel, also dead — see below). All composer call sites use `QueryComposer` / `FollowUpComposer`. |
| `src/components/v2/index.ts` | `rg "from ['\"']@/components/v2['\"']"` → 0 hits (everyone imports from individual files). |

### Whole-export deletes (file stays, drop the unused function)

| Export | File | Why |
|---|---|---|
| `largestRetentionDropAnnotation` | `src/components/v2/retentionCurveMath.ts` | No callers; the rest of the file is used by retention-curve charts. |
| `useCreateSession`, `useInsertUserMessage` | `src/hooks/useChatSession.ts` | Both wrote into `chat_messages` from `ChatScreen`, which Phase C.7 deleted. The file's other exports (`chatKeys`, `useChatSession`) are still used by `ChatSessionReadScreen` and `useSessionStream`. |
| `useScriptDrafts` | `src/hooks/useScriptSave.ts` | No caller. Other `useScript*` exports in the file remain in use. Confirm with `tools/scripts` PM that the drafts list is not a near-term feature; otherwise demote to "Tier 2 — wire it". |
| `useInvalidateAnswerSessions` | `src/hooks/useAnswerSessionQueries.ts` | Common pattern to publish a manual invalidator, but nobody calls it. Safe to drop — any future caller can add it back in three lines. |

Process per file:

1. `git rm <file>` (or remove the export).
2. `npm run typecheck` (TS will flag any reference tooling missed).
3. `npm test`.
4. **One commit per concern**, e.g.:
   - `lib: remove unused src/lib/constants.ts (superseded by db + cloud-run)`
   - `lib/batch: remove client-side classifier + quality-gate (Python is canonical)`
   - `components/v2: remove dead Composer and barrel index`
   - `components/ui: remove unused Card primitive`
   - `hooks/useChatSession: drop unused mutations after C.7 chat deletion`

---

## Tier 4 — make this audit repeatable

### T1 — Add a `knip.json` (only after Tiers 1–3 land)

Without config, knip flags every Deno function, every shadcn primitive,
and every artifact file. The first run after cleanup should be quiet:

```json
{
  "$schema": "https://unpkg.com/knip@5/schema.json",
  "entry": [
    "src/root.tsx",
    "src/routes.ts",
    "src/routes/**/route.tsx",
    "api/**/*.ts",
    "scripts/**/*.{ts,mjs}"
  ],
  "project": ["src/**/*.{ts,tsx}", "api/**/*.ts"],
  "ignore": [
    "src/make-import/**",
    "src/components/ui/**",
    "artifacts/**",
    "mobile/**",
    "supabase/functions/**",
    "cloud-run/**"
  ],
  "ignoreDependencies": [
    "@radix-ui/*",
    "@react-router/dev",
    "@react-router/node",
    "tailwindcss",
    "tw-animate-css"
  ]
}
```

Then `npm run knip` (just `knip`) and CI gate **after** Tiers 1–3.

### T2 — Wire ruff into Cloud Run CI

`cloud-run/pyproject.toml` already configures ruff (`E`, `F`, `I`,
`UP`). Add to CI (or `.pre-commit-config.yaml`):

```yaml
- run: cd cloud-run && python3 -m ruff check getviews_pipeline main.py
```

This keeps Tier-B1 from regressing.

### T3 — Drop `ts-prune`

`ts-prune` flagged ~80 lines, of which ~50 are RR convention
(`default` / `meta` / `loader` / `Layout`) or `.react-router/types/**`
virtual files. The signal-to-noise ratio is bad for an RR app. Use
knip + manual `rg` audits instead.

---

## Sequencing

| Day | Work | Risk | Output |
|---|---|---|---|
| 1 | B1 (`ruff --fix`) + B2 (`npm uninstall …`) | Near-zero | One PR, two commits. |
| 2 | Tier 3 whole-file + whole-export deletes | Low — TypeScript will catch any miss | One PR, one commit per concern (see list). |
| 3 | Tier 2 product decisions written up as **proposals** (PRs that delete + amend the spec, or PRs that wire the missing UI). Do not merge without sign-off. | Medium — touches product surface | One PR per decision area (chat widgets, step logger, install prompt, resolveDestination test). |
| 4 | Tier 4 tooling (knip config + ruff CI + drop ts-prune) | Low | One PR. |

## Out-of-scope follow-ups

- **`src/make-import/**`** — excluded from `tsconfig.app.json`, but the
  legacy `check-tokens` script still lints it and fails. Decide:
  delete the tree or carve it out of `check-tokens` for good.
- **`artifacts/uiux-reference/uploads/LandingPage.tsx`** — a `.tsx`
  under `artifacts/`. Either move it under `src/` if it ships, or leave
  it and add to knip's ignore list.
- **Re-run the audit after each tier** so leftover noise drops
  monotonically — that's the only way to tell whether T1 (knip config)
  is doing its job.
