# Phase B · B.2 — supplementary design parity (resolved)

**Date:** 2026-04-19  
**Scope:** Shell + `/app/kol` parity vs `artifacts/uiux-reference/screens/kol.jsx`, `phase-b-plan.md` §B.2, and acceptance QA (sidebar, kickers, avatar tokens, ribbon, server search, pinned empty, tone cleanup, tests).

**Automated checks (acceptance):** `cloud-run/tests/test_kol_browse.py` — includes **`test_run_kol_browse_search_filters_rows`** (partial handle + name). `npx vitest run` — includes **`MatchScoreBar.test.tsx`** (3 clamp/round cases). `grep -E '\.tone'` on `SortableCreatorsTable.tsx` and `kol_browse.py` → no matches (S-4 drop). Hex in touched KOL JSX files: none (`#[0-9a-fA-F]{3,6}` only in `src/app.css` for `--gv-avatar-*` definitions).

| ID | Item | Resolution | Status |
|----|------|------------|--------|
| M-1 | Sidebar **Kênh Tham Chiếu** live + nav active | `AppLayout.tsx`: `NavItem` → `navigate("/app/kol")`, `active={active === "kol"}`; `AppLayoutProps.active` / `BottomTabBar` accept `"kol"`. `KolScreen.tsx`: `<AppLayout active="kol">`. | ✅ Shipped |
| M-2 | Single kicker (no double “studio”) | `TopBar` `kicker="THEO DÕI"`; hero block keeps `KÊNH THAM CHIẾU · NGÁCH …`. | ✅ Shipped |
| M-3 | Avatar palette → design tones, no lime | `src/app.css`: `--gv-avatar-1..6`; `kolAvatarPalette.ts` + `SortableCreatorsTable` / `KolStickyDetailCard` index sync; lime removed from cycle. | ✅ Shipped |
| S-1 | Filter ribbon **LỌC THEO** kicker | Stacked mono label above chips; `FilterChipRow` `label=""` when label rendered externally. | ✅ Shipped |
| S-2 | Server-side search | `run_kol_browse_sync(..., search=)` + `_filter_decorated_by_search`; `GET /kol/browse?search=`; `useKolBrowse` query key + debounced 250ms in `KolScreen`; client `filtered` removed. | ✅ Shipped |
| S-3 | Pinned-tab empty state | `rows.length === 0 && tab === "pinned"` → card + **Mở Khám phá** → `setTab("discover")`. | ✅ Shipped |
| S-4 | `tone` dead-branch cleanup | Dropped `tone` from API `decorate()`, `KolBrowseRow`, and creator subline in `SortableCreatorsTable`. | ✅ Shipped |

**Explicitly unchanged (per constraints):** Match-score formula and weights; growth display still uses **avg_views percentile proxy**; match scores still **recomputed per request** (no new persistence); other `cloud-run/tests/` collection issues pre-existing.

---

## Shipped in commit (per M / S item)

**Bundle:** `673a42d` — `fix(kol): supplementary M/S parity — shell, ribbon, search, avatars, tests`

| ID | Shipped in commit | Notes |
|----|-------------------|--------|
| M-1 | `673a42d` | `AppLayout` + `BottomTabBar` `AppShellActive`; live sidebar link + `active="kol"` on `KolScreen`. |
| M-2 | `673a42d` | `TopBar` kicker `THEO DÕI` vs hero `KÊNH THAM CHIẾU · NGÁCH`. |
| M-3 | `673a42d` | CSS tokens `--gv-avatar-1..6`; shared `kolAvatarPalette`; detail card `avatarPaletteIndex` prop. |
| S-1 | `673a42d` | `KolScreen` stacked **LỌC THEO**; `FilterChipRow` conditional inline label. |
| S-2 | `673a42d` | `kol_browse.py` + `main.py` + `useKolBrowse.ts` + `KolScreen` debounced `search`. |
| S-3 | `673a42d` | Pinned empty card + CTA to discover tab. |
| S-4 | `673a42d` | Tone field removed end-to-end; `MatchScoreBar.test.tsx` added. |

**Earlier B.2 screen + API baseline:** `7d77a80` — `feat(kol): ship Phase B.2 Kênh Tham Chiếu screen and API` (browse, toggle-pin, `KolScreen` v1, Playwright B.2.3, audits).
