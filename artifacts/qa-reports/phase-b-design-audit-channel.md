# Phase B · B.3.5 design audit — `/app/channel`

**Date:** 2026-04-19  
**Sources:** `artifacts/uiux-reference/screens/channel.jsx` + `artifacts/plans/phase-b-plan.md` §B.3.3 / §B.3.5  
**Shipped UI:** `src/routes/_app/channel/ChannelScreen.tsx`, `src/routes/_app/channel/route.tsx`, `src/components/v2/FormulaBar.tsx` (reused: `SectionMini`, `KpiGrid`, `TopBar`, `Chip`, `Btn`).

---

## Token & banned-pattern sweep

**Scope:** `src/routes/_app/channel/**/*.tsx`, `src/components/v2/FormulaBar.tsx`

| Check | Result |
|--------|--------|
| Raw `#hex` in JSX | **0 matches** |
| `--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*` | **0 matches** |
| `rgba(` / `rgb(` in channel route + FormulaBar | **0 matches** |
| Primary surfaces | Colors use `var(--gv-*)` or `rounded-[var(--gv-radius-md)]` |

**API-driven:** `style={{ backgroundColor: v.bg_color }}` on video tiles when the corpus returns a swatch — acceptable per B.3.3 audit (not author-chosen hex in source).

---

## Section-by-section vs `channel.jsx`

| Block | Reference (`channel.jsx`) | Shipped | Tier |
|--------|---------------------------|---------|------|
| Shell | `maxWidth: 1280`, padding `24px 28px 80px` | `gv-route-main gv-route-main--1280` (same spec in `app.css`) | OK |
| Back | Ghost + “Về Studio”, `marginBottom: 18` | `Btn` ghost + copy; spacing aligned to **18px** | **must-fix** → fixed |
| Hero container | `padding: 28px 32px`, `borderRadius: 12`, `gap: 32` | `px-8 py-7`, `rounded-[12px]`, `gap-8` / `min-[900px]:grid-cols-2` | **must-fix** → fixed |
| Kicker | `HỒ SƠ KÊNH · {niche}`, mono uc ~9.5px, ink-4 | `gv-uc` + `text-[9.5px]` + `gv-ink-4` | OK |
| Avatar | 64×64, accent fill, initial ~22px | `h-16 w-16`, `gv-accent`, `text-[22px]` | OK |
| Name / handle row | tight 38px; mono 12px ink-3 | `gv-tight text-[38px]`; `text-xs` mono ink-3 | OK |
| Bio | italic 18px ink-2, maxWidth 460 | `text-lg italic` + `max-w-[460px]` + ink-2 | OK |
| Chips | `gap: 8`, `marginTop: 18`; cadence + engagement + count | `gap-2`, **`mt-[18px]`**; posting joined with ` · ` (B.3.3); `Chip` variants | **must-fix** → fixed |
| KPI strip | 2×2 in hero right, rule border, radius 10, pad 18 | `KpiGrid` (matches B.1 / reference) | OK |
| Formula kicker/title | `CÔNG THỨC PHÁT HIỆN`; `"{name} Formula" — 4 bước…` | Same kicker; title uses **“4 bước lặp đi lặp lại”** | **must-fix** → fixed |
| Formula bar | Height 80, `borderRadius: 8`, `border: 1px solid ink`, 4 flex segments, token colors | `h-20`, `rounded-lg` (8px), `border-gv-ink`, segment stack | OK |
| Thin corpus | Empty bar, mono 11px ink-4, prescribed copy | `FormulaBar` — B.3.3 must-fix copy + ink-4 | OK |
| Two-col grid | `gap: 32`, 900px stack | `gap-8`, `min-[900px]:grid-cols-2` | OK |
| Video tiles | 2×2, gap 12, thumb radius 6, mono views | `gap-3`, `rounded-md`, views row | OK |
| Video section title | “Top 4 video gây tiếng vang” | Aligned to reference string | **must-fix** → fixed |
| Lessons | Card pad 14, gap 12, index accent-deep, title 13px | `p-3.5`, `gap-3`, mono index, `text-[13px]` title | OK |
| Script CTA | Full-width accent | `Btn` accent, disabled until `/script` | OK (stub) |

---

## must-fix (closed in this audit PR)

1. **B.3.3 compliance (re-verified):** `FormulaBar` thin state — “Chưa đủ video để dựng công thức” + `gv-ink-4`. Posting chip — `posting_cadence · posting_time` when both set. *(Already on `main`; re-checked.)*
2. **Hero padding:** `28px` vertical × `32px` horizontal → `px-8 py-7` on hero card.
3. **Back row spacing:** `18px` below back control → `mb-[18px]`.
4. **Chip row:** `marginTop: 18` → `mt-[18px]`.
5. **Copy parity:** Formula section title “4 bước…”; video block title “Top 4 video…”.

---

## should-fix

| Item | Note |
|------|------|
| TopBar + pulse | Extra chrome vs static reference — product choice; keep for parity with `/app/video`. |
| “Kênh khác” form | Not in reference; useful for deep-link UX — keep. |

---

## consider

| Item | Note |
|------|------|
| Vertical rhythm | Reference mixes `mb: 28` (hero) and `36` (formula block); uniform `gap-7`/`gap-8` is close enough unless pixel-perfect pass requested. |
| `PostingHeatmap` | Still deferred per plan. |

---

## Verdict

**Green for B.3.5 closure:** token sweep clean; section-by-section parity **must-fix** items above are implemented; remaining gaps are **should-fix** / **consider** only.

Follow-up: keep `artifacts/qa-reports/phase-b-b33-channel-audit.md` as the narrower B.3.3 compliance note; this file is the **design-audit** artifact required by §B.3.5.
