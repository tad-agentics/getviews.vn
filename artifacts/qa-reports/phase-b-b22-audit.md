# B.2.2 audit — `/app/kol` (interim, pre–B.2.4 design audit)

Date: 2026-04-19. Source: `artifacts/plans/phase-b-plan.md` § Frontend `/app/kol` + fixture mapping + milestones B.2.2.

## Pass (aligned with plan)

| Requirement | Evidence |
|-------------|----------|
| Route + lazy screen | `src/routes/_app/kol/route.tsx`, `src/routes.ts` → `app/kol` |
| `GET /kol/browse` + `POST /kol/toggle-pin` | `src/hooks/useKolBrowse.ts` |
| Tab deep-link `?tab=pinned\|discover` | `KolScreen.tsx` `useSearchParams`, `setTab` resets `page` to 1 |
| Optimistic pin + profile invalidation | `useKolTogglePin` `onMutate` / `onSettled` |
| Primitives | `FilterChipRow`, `SortableCreatorsTable`, `MatchScoreBar`, `KolStickyDetailCard` under `src/components/v2/` |
| Sticky detail `top: 86px` at ≥1100px | `KolStickyDetailCard` + desktop wrapper `hidden min-[1100px]:block`; mobile copy `sticky={false}` |
| Token hygiene (KOL route/components) | Grep on `src/routes/_app/kol` + related v2 KOL files: no `#[0-9a-fA-F]{3,8}` / banned `--gv-purple*` / `--ink-soft` in those paths |
| Cloud Run gated + empty niche | `VITE_CLOUD_RUN_API_URL`, `primary_niche` messaging |
| GHIM in discover | `SortableCreatorsTable` + `tab === "discover"` |

## Gaps — **closed** (2026-04-19)

| Item | Resolution |
|------|------------|
| **Server-side filters** | `GET /kol/browse?followers_min&followers_max&growth_fast`; URL `?followers=` presets + `?growth=1`; discover tab count uses same filters. |
| **Pagination UX** | Trước/Sau + page label; `?page=` synced. |
| **`match_description`** | Cloud Run sets per row; card prefers API string with `kol.jsx`-aligned fallback. |
| **B.2.4** | See **`artifacts/qa-reports/phase-b-design-audit-kol.md`** (GREEN). |

## Out of scope for B.2.2 (explicit)

- `/app/channel`, `/app/script` CTAs — correctly disabled pending B.3 / B.4.
- **`creator_search` in chat** when user **types** a KOL query — not a “CTA”; B.2.3 targets quick-action / empty-state entry only.

## B.2.3 follow-up (implemented separately)

- Home `QuickActions` + chat empty-state “Tìm KOL” must route to `/app/kol`; remove modal → `creator_search` path for that CTA.
