# Phase D.0.iii — Token dualism rebind map

**Date:** 2026-04-20
**Blocks:** D.4 (token namespace deprecation)
**Status:** Locked

---

## Inventory

Grep run on `main` at 2026-04-20:

```
grep -rlE 'var\(--(purple|purple-light|ink-soft|border-active)\)|\
--gv-purple|variant="purple"' src/
```

**39 files** total (plan estimated 38; 1-file drift tolerated). Breakdown:

| Cluster | File count | D.4.1 commit | Files |
|---|---|---|---|
| `src/components/ui` | 4 | **D.4.1.a** (first — lowest primitive) | `Badge.tsx`, `Button.tsx`, `Card.tsx`, `Input.tsx` |
| `src/components/chat` | 9 | **D.4.1.b** | `AgentStepLogger.tsx`, `CopyableBlock.tsx`, `CreatorGridCard.tsx`, `FollowUpChips.tsx`, `StepSpinner.tsx`, `StepThumbnails.tsx`, `TrendCard.tsx`, `TrendingSoundCard.tsx`, `VideoRefCard.tsx` |
| `src/components/explore` | 4 | **D.4.1.c** | `TrendingSection.tsx`, `TrendingSoundsSection.tsx`, `VideoDangHocSidebar.tsx`, `VideoPlayerModal.tsx` |
| `src/routes/_app/components` | 11 | **D.4.1.d** (largest cluster) | `AnalysisLimitCard.tsx`, `CopyButton.tsx`, `CreatorCard.tsx`, `CreditBar.tsx`, `DiagnosisRow.tsx`, `EmptyStates.tsx`, `MorningRitualBanner.tsx`, `PromptCards.tsx`, `QuickActionModal.tsx`, `ThumbnailStrip.tsx`, `URLChip.tsx` |
| `src/routes/_app/{checkout,history,learn-more,payment-success,pricing,settings,trends}` | 7 | **D.4.1.e** (legacy-layout screens — token-only, 0 JSX changes) | `CheckoutScreen.tsx`, `ChatSessionReadScreen.tsx`, `LearnMoreScreen.tsx`, `PaymentSuccessScreen.tsx`, `PricingScreen.tsx`, `SettingsScreen.tsx`, `ExploreScreen.tsx` |
| `src/routes/_auth` | 2 | **D.4.1.f** | `callback/route.tsx`, `login/route.tsx` |
| `src/routes/_index` | 1 | **D.4.1.e** (grouped with legacy-layout screens) | `LandingPage.tsx` |
| `src/app.css` (legacy defs) | 1 | **D.4.2** (last — deletes defs) | `app.css` |

Total = 39. The plan's D.4.1.e cluster absorbs both the 7 `_app` single-file
screens and the single `_index/LandingPage.tsx` because the legacy-layout
rule applies to all eight (strict token-only; 0 JSX structure changes).

---

## Rebind map

| Legacy | Replacement | Notes / per-consumer judgment |
|---|---|---|
| `var(--purple)` | `var(--gv-accent)` | TikTok brand pink (`#FE2C55`) is the post-pivot accent. Decorative uses (e.g. background tints on `TrendCard`) may prefer `var(--gv-accent-soft)`; verify per consumer before committing. |
| `var(--purple-light)` | `var(--gv-accent-soft)` | Used almost exclusively for tint backgrounds (user-message bubble, selection states). 1:1 swap. |
| `var(--ink-soft)` | `var(--gv-ink-3)` | Body text / secondary label color. C.6 `/history` audit confirmed the swap is 1:1; apply without further judgment. |
| `var(--border-active)` | `var(--gv-rule)` (default) or `var(--gv-ink)` (emphasised) | Per-consumer judgment. Active-state borders on form inputs use `--gv-ink`; neutral dividers use `--gv-rule`. |
| `Badge variant="purple"` | `Badge variant="default"` | After D.4.1.a lands the deprecation shim (`console.warn` + map to `default`), all call sites swap to `variant="default"` explicitly. Never reintroduce the `purple` variant. |

---

## Commit ordering (D.4.1 phase)

Order matters — `Badge` (D.4.1.a) ships first so downstream
`variant="purple"` consumers inherit the deprecation shim immediately.
The 8 legacy-layout screens (D.4.1.e) ship last because their blast
radius is highest (landing, checkout, pricing — all seen by
conversion-critical flows).

1. **D.4.1.a** — `src/components/ui` (4 files). Badge ships the
   deprecation shim; Button / Card / Input swap tokens in place.
2. **D.4.1.b** — `src/components/chat` (9 files). Legacy chat
   primitives (pre-Phase C deletion) still referenced by
   `/app/history/chat/:sessionId` readonly transcript viewer.
3. **D.4.1.c** — `src/components/explore` (4 files). Explore-rail
   primitives on `/app/trends`.
4. **D.4.1.d** — `src/routes/_app/components` (11 files). Shared
   components across creator screens; biggest cluster.
5. **D.4.1.e** — legacy-layout screens (8 files: 7 `_app` screens +
   `LandingPage.tsx`). **Token-only. 0 JSX structure changes asserted
   against `git diff --stat`.** Per Phase D Pre-kickoff rule 6.
6. **D.4.1.f** — `src/routes/_auth` (2 files). `callback/route.tsx`
   + `login/route.tsx`.

**D.4.2** (`src/app.css`) — **only after** all six clusters report 0
legacy-token hits. Deletes `--purple`, `--purple-light`, `--ink-soft`,
`--border-active` definitions. Estimated ~18 LOC deletion.

**D.4.3** — CI lint rule `scripts/check-tokens.mjs` (new) + wiring into
`npm run typecheck` and CI. Deliberate-test-PR pattern: introducing
`var(--purple)` on any path fails; removing passes.

---

## Per-cluster grep commands

For each cluster commit, run before / after to assert 0 hits in the
cluster directory:

```bash
# D.4.1.a
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/components/ui/

# D.4.1.b
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/components/chat/

# D.4.1.c
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/components/explore/

# D.4.1.d
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/routes/_app/components/

# D.4.1.e (8 files — specify paths explicitly because the legacy-layout rule applies to all of them)
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' \
  src/routes/_app/checkout/ \
  src/routes/_app/history/ChatSessionReadScreen.tsx \
  src/routes/_app/learn-more/ \
  src/routes/_app/payment-success/ \
  src/routes/_app/pricing/ \
  src/routes/_app/settings/ \
  src/routes/_app/trends/ \
  src/routes/_index/

# D.4.1.f
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/routes/_auth/

# D.4.2 (workspace-wide, excludes src/app.css during final delete)
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/ --exclude=src/app.css
```

---

## Deliberate scope-guard on D.4.1.e

The 8 legacy-layout files in D.4.1.e are the **three screens whose
layout revamps are deferred indefinitely** (per Phase D plan §D.4 and
Deferred section) plus their siblings on the `_app` routes. The token
purge is allowed to rebind `className` + `style` property values. It
is NOT allowed to:

- Add, remove, or reorder JSX elements.
- Change component prop shapes or add new props.
- Migrate from one primitive to another (e.g. legacy `Badge` → some
  new component).
- Touch hooks, query keys, or data flow.

Acceptance check for D.4.1.e commit:

```bash
# Before and after the token swap, assert 0 element insertions/removals:
git diff --stat src/routes/_app/{checkout,history,learn-more,payment-success,pricing,settings,trends}/ src/routes/_index/
# Only `className` / `style` property value changes should appear.
```

Any D.4.1.e commit that restructures these files fails Phase D
sign-off per Pre-kickoff rule 6.

---

## Verification after D.4.2

After `src/app.css` defs are deleted, the final workspace grep is
expected to return 0 hits across all of `src/`:

```bash
grep -rnE 'var\(--(purple|purple-light|ink-soft|border-active)\)|--gv-purple|variant="purple"' src/ 2>&1 | wc -l
# Expected: 0
```

D.4.3 CI lint rule locks that invariant forward.

---

## Sign-off

Inventory locked at 39 files. Cluster assignment matches the plan's
D.4.1.a-f commits. Rebind map covers all five legacy namespace
references. Scope-guard on D.4.1.e documented.

**Deliverable merged; unblocks D.4 kickoff.**
