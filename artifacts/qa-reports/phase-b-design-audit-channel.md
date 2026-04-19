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
| Bio | italic 18px ink-2, maxWidth 460, **lh 1.4** | `text-lg italic` + `max-w-[460px]` + **`leading-[1.4]`** | **must-fix** → fixed |
| Chips | `gap: 8`, `marginTop: 18`; cadence + engagement + count | `gap-2`, **`mt-[18px]`**; posting joined with ` · ` (B.3.3); `Chip` variants | **must-fix** → fixed |
| KPI strip | 2×2 in hero right, rule border, radius 10, pad **18**, cells **canvas**, value **22px** lh **1.1**, label mb **4px**, delta mt **4px** | `KpiGrid variant="channel"` (video strip unchanged) | **must-fix** → fixed (see `phase-b-b3-full-audit.md`) |
| Formula kicker/title | `CÔNG THỨC PHÁT HIỆN`; `"{name} Formula" — 4 bước…` | Same kicker; title uses **“4 bước lặp đi lặp lại”** | **must-fix** → fixed |
| Formula bar | Height 80, `borderRadius: 8`, `border: 1px solid ink`, detail **lh 1.3** | `h-20`, `rounded-[8px]`, ink border, **`leading-[1.3]`** on detail | **must-fix** → fixed |
| Thin corpus | Empty bar, mono 11px ink-4, prescribed copy | `FormulaBar` — B.3.3 must-fix copy + ink-4 | OK |
| Two-col grid | `gap: 32`, **max-width 900px** → 1 col | `gap-8`, **`min-[901px]:grid-cols-2`** + `grid-cols-1`; **`mt-9`** after formula | **must-fix** → fixed |
| Video tiles | 2×2, gap 12, thumb radius 6, mono views, **no** extra border / icon | `gap-3`, `rounded-md`, overlay only | **must-fix** → fixed |
| Video section title | “Top 4 video gây tiếng vang” | Aligned to reference string | **must-fix** → fixed |
| Lessons | Card pad 14, gap 12, index accent-deep, title 13px **mb 2** | `p-3.5`, `gap-3`, index; title **`mb-0.5`** | **must-fix** → fixed |
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
| `PostingHeatmap` | Still deferred per plan. |
| Extra shell chrome | `TopBar`, “Kênh khác” form — product choice vs static reference. |

---

## Verdict

**Green for B.3.5 closure:** token sweep clean; section-by-section parity **must-fix** items (including KPI `channel` variant, **36px** rhythm, **901px** breakpoint, video tile chrome, line-heights) are implemented — see **`phase-b-b3-full-audit.md`** for the consolidated B.3 closure report.

Follow-up: keep `artifacts/qa-reports/phase-b-b33-channel-audit.md` as the narrower B.3.3 compliance note; this file is the **design-audit** artifact required by §B.3.5.
