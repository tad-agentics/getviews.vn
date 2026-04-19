# B.2 checkpoint — `/kol` Kênh Tham Chiếu

**Date:** 2026-04-19  
**Plan:** `artifacts/plans/phase-b-plan.md` §B.2  
**Verdict:** **GREEN** — milestones B.2.1–B.2.5 are implemented and consistent with the closed design audit, with documented plan deltas below.

---

## Milestone matrix

| ID | Deliverable | Status | Evidence |
|----|-------------|--------|------------|
| **B.2.1** | `toggle_reference_channel` RPC (cap 10) + browse + toggle-pin + tests | **Shipped** | `supabase/migrations/20260426000052_b21_kol_toggle_reference_channel.sql`; `GET /kol/browse`, `POST /kol/toggle-pin` in `cloud-run/main.py`; `cloud-run/getviews_pipeline/kol_browse.py`; `cloud-run/tests/test_kol_browse.py` (11 passed) |
| **B.2.2** | `/app/kol` screen (table, filters, sticky card, URL tab, mutation) | **Shipped** | `src/routes.ts` → `app/kol`; `src/routes/_app/kol/{route.tsx,KolScreen.tsx}`; `src/hooks/useKolBrowse.ts`; v2: `FilterChipRow`, `SortableCreatorsTable`, `MatchScoreBar`, `KolStickyDetailCard`; `src/lib/api-types.ts` `KolBrowse*` |
| **B.2.3** | Retire chat as primary entry for “Tìm KOL”; route to `/app/kol` | **Shipped** | `QuickActions.tsx` `kol → /app/kol`; `EmptyStates.tsx` “Tìm KOL / Creator” → `href: /app/kol`; Playwright `tests/quick-actions.spec.ts` (B.2.3) |
| **B.2.4** | Design audit + must-fix | **GREEN** | `artifacts/qa-reports/phase-b-design-audit-kol.md`; token grep on `src/routes/_app/kol/**` + v2 KOL table files: **no** raw `#hex` / banned purple-era tokens in those paths |
| **B.2.5** | `kol_screen_load`, `kol_pin` + smoke script | **Shipped** | `KolScreen.tsx` → `logUsage`; `src/lib/logUsage.ts`; `artifacts/qa-reports/smoke-kol.sh` + `artifacts/qa-reports/phase-b-b25-measurement.md` |

---

## Rule-based match (B.0.2 / B.2 fixture)

- **Weights:** `0.40 niche + 0.30 followers + 0.20 growth + 0.10 ref_overlap` — implemented in `compute_match_score()` (`kol_browse.py`).
- **Growth term:** Plan and fixture table cite `creator_velocity.growth_30d_pct` / niche percentile. **Current code** uses `growth_percentile_from_avgs()` — **avg_views rank within niche** as a **proxy** for the 0.20 term (same family as displayed “TĂNG 30D” proxy). Documented in design audit resolved S2.
- **Caching:** Plan text says cache per `(user_id, handle)`. **Current:** recomputed on each browse (module docstring: no persistence). Acceptable v1; list as **follow-up** if DB load becomes an issue.

---

## API vs plan spec

| Plan | Shipped |
|------|---------|
| `GET /kol/browse?niche_id&tab&page` | Same + `page_size`, `followers_*`, `growth_fast`, **`sort`**, **`order_dir`** (B.2.4 close-out) |
| `POST /kol/toggle-pin` `{ handle }` | Matches; RPC `toggle_reference_channel` |

---

## Chat / intent note

- **`creator_search` / `find_creators`** still exist as **chat pipeline intents** (sessions, API, Cloud Run). B.2.3 scope was **entry UX**: primary “Tìm KOL” doors go to **`/app/kol`**, not opening a dedicated chat finder first. No change required for checkpoint unless product wants to block chat-side creator search entirely.

---

## Automated checks (this run)

| Check | Result |
|-------|--------|
| `python3 -m pytest cloud-run/tests/test_kol_browse.py -q` | **11 passed** |
| `npm run build` (repo root) | **Passed** (pre-existing Vite/tsconfig noise unrelated to B.2) |
| Full `cloud-run/tests/` | **Collection errors** in `test_gate_schema_alignment.py`, `test_intent_routing.py` (pre-existing; not B.2 regressions) |

---

## Open product items (from audit “consider”, not B.2 blockers)

- **C1** — Việt Nam region chip: needs `country` on corpus/model.  
- **C2** — “+ Thêm điều kiện” advanced sheet: deferred.  
- **C3** — Search box scopes **current page** after fetch; full-corpus search would need a new endpoint.

---

## Sign-off

B.2 is **checkpoint-complete** for implementation: backend contract, Supabase RPC, web route, B.2.3 navigation, design audit gate, and B.2.5 instrumentation/smoke are in place. Remaining deltas are **data truth** (real 30d growth when available) and **optional persistence** for match scores, not missing screen work.
