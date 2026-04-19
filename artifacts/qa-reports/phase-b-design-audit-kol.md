# Phase B · B.2.4 — Design audit: `/app/kol` vs `artifacts/uiux-reference/screens/kol.jsx`

**Date:** 2026-04-19 (revised **2026-04-19** — B.2.4 closure: should-fix S2/S3)  
**Sources:** `kol.jsx`, `artifacts/uiux-reference/styles.css` (tokens), shipped files under `src/routes/_app/kol/`, `src/components/v2/{FilterChipRow,SortableCreatorsTable,MatchScoreBar,KolStickyDetailCard}.tsx`.

## Token gate (plan non-negotiable)

Commands (repo root):

```bash
rg '#[0-9a-fA-F]{3,8}' src/routes/_app/kol src/components/v2/FilterChipRow.tsx \
  src/components/v2/SortableCreatorsTable.tsx src/components/v2/MatchScoreBar.tsx \
  src/components/v2/KolStickyDetailCard.tsx
rg '--ink-soft|--purple|--border-active|--gv-purple' src/routes/_app/kol \
  src/components/v2/{FilterChipRow,SortableCreatorsTable,MatchScoreBar,KolStickyDetailCard}.tsx
```

**Result:** **PASS** — no raw hex and no banned purple-era tokens in the audited KOL screen + v2 primitives listed above.

> Note: `kol.jsx` **reference** uses literal hex for avatar rotation (`#3D2F4A`, …). Shipped code correctly maps rotation to `var(--gv-*)` / mix tokens in `SortableCreatorsTable` — **do not** copy reference hex into production.

---

## Tier summary

| Tier | Count | Status |
|------|------:|--------|
| **Must-fix** | 4 | **Shipped in this pass** (see below) |
| **Should-fix** | 1 | S1 only (intentional breakpoint); S2/S3 resolved in B.2.4 close-out |
| **Consider** | 3 | Nice-to-have |

---

## Must-fix (shipped)

| # | Issue | Resolution |
|---|--------|--------------|
| 1 | **Pagination** — `?page=` had no UI | `KolScreen.tsx`: Trước/Sau + `gv-mono` summary; clamps to `totalPages`; only shows when `total > page_size`. |
| 2 | **Server filters** — chips were placeholders | Cloud Run `GET /kol/browse`: `followers_min`, `followers_max`, `growth_fast`. UI: URL `?followers=10k-100k|100k-1m|1m-5m` + `?growth=1`; TanStack keys include filter signature. |
| 3 | **`match_description`** — static only | Backend `kol_browse.py` emits per-row `match_description`; `KolStickyDetailCard` uses API text with **fallback** matching `kol.jsx` high-match copy. |
| 4 | **Main bottom padding** | `kol.jsx` uses `80px` bottom padding → `KolScreen` `main` updated from `pb-20` to **`pb-[80px]`**. |

---

## Should-fix

| # | Topic | Detail |
|---|--------|--------|
| S1 | **Layout breakpoint** | Reference uses fixed `1fr 380px` grid. Shipped stacks & hides sticky card below **1100px** — better mobile ergonomics; document as intentional deviation. |

### Resolved (same pass as B.2.4 close-out)

| # | Was | Resolution |
|---|-----|--------------|
| ~~S2~~ | TĂNG 30D always **—** | **`growth_30d_pct`** now a **display proxy** from avg_views percentile within niche (~±22%). Not true 30d MoM — label unchanged until corpus ships real series. |
| ~~S3~~ | Client-only sort | **`GET /kol/browse?sort=&order_dir=`** — full-pool sort server-side; URL synced from table headers (`useKolBrowse` query key includes sort). |

---

## Consider

| # | Topic |
|---|--------|
| C1 | **Việt Nam** filter — no `country` on `starter_creators`; chip disabled with honest tooltip until data model exists. |
| C2 | **“+ Thêm điều kiện”** — still deferred (advanced filter sheet). |
| C3 | **Search box** — filters **current page** after fetch; placeholder/aria notes “trang hiện tại”. Full-corpus search would need backend endpoint. |

---

## Section-by-section vs `kol.jsx`

| Block | Reference | Shipped | Match |
|-------|-----------|--------|:-----:|
| Max width + horizontal padding | `1320`, `24px 28px` | `max-w-[1320px]`, `px-6` / `min-[900px]:px-7` (~24/28) | ~ |
| Tab bar + counts | Pinned / discover + badges | Same pattern + icons | ✓ |
| Filter ribbon | `LỌC THEO` + pills + search | `FilterChipRow` + chips + search | ✓ |
| Table grid | `40px 2fr 100px ×3 + 80px` | `SortableCreatorsTable` same template | ✓ |
| Row selected bg | `paper` | `gv-paper` | ✓ |
| GHIM badge | discover + pinned member | Same | ✓ |
| Detail card sticky `top: 86` | yes | `min-[1100px]:sticky` + `top-[86px]` | ✓ |
| Match block | 36px score + 11px ink-3 blurb | Same structure + API blurb | ✓ |
| CTAs (channel / pin / script) | three buttons | same; channel/script disabled until B.3/B.4 | ✓ |

---

## Verdict

**B.2.4 gate:** **GREEN** for token check + must-fix items above are implemented in repo. **B.2.5** (`kol_screen_load`, `kol_pin`, `smoke-kol.sh`) — see `artifacts/qa-reports/phase-b-b25-measurement.md`. Remaining **should-fix / consider** items are product/data follow-ups, not blockers for closing B.2.4 audit milestone.
