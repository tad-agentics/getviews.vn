# B.2.3 audit — Retire KOL chat CTA, route “Tìm KOL” to `/app/kol`

**Date:** 2026-04-19  
**Plan ref:** `artifacts/plans/phase-b-plan.md` milestone **B.2.3**.

## Requirements vs implementation

| Requirement | Status | Evidence |
|-------------|:------:|----------|
| Retire `find_creators` / **`creator_search` chat CTA** (modal → stream) | **Pass** | `EmptyStates.tsx`: “Tìm KOL / Creator” uses `href: "/app/kol"` + `Users` icon; `tim-kol` removed from `QuickActionModal` configs. |
| **“Tìm KOL”** home quick-action → `/app/kol` | **Pass** | `QuickActions.tsx` `ROUTE.kol = "/app/kol"`. |
| Typed chat still may use `creator_search` | **Pass (intentional)** | `intent-router.ts` unchanged; plan cross-cutting note: typed NL can still hit Cloud Run pipeline. |
| Tests / regression | **Pass** | `tests/quick-actions.spec.ts`: chat empty-state + home navigation tests for `/app/kol`; modal stream cases no longer include `tim-kol`. |

## Grep checks

- `tim-kol` in `src/`: **none** (modal key retired).
- `kol: "/app/chat"` in `QuickActions`: **none**.

## Verdict

**B.2.3: GREEN** — quick-entry surfaces route to the dedicated KOL screen; chat modal path for this intent is removed.
