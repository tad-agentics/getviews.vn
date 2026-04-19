# Phase B · B.3 full audit — implementation + pixel parity

**Date:** 2026-04-19  
**Plan:** `artifacts/plans/phase-b-plan.md` §B.3 (`/channel` Phân Tích Kênh)  
**Design reference:** `artifacts/uiux-reference/screens/channel.jsx` + §B.3 “Exact design spec”

This document supersedes scattered notes for **closure of B.3**: milestones B.3.1–B.3.5, backend + web + routing + chat handoff, and **pixel-level** comparison to the reference (with explicit deltas and fixes).

---

## 1. Milestone checklist (B.3.1–B.3.5)

| Milestone | Requirement (plan) | Evidence / status |
|-----------|----------------------|---------------------|
| **B.3.1** | `channel_formulas` migration, ≥10 video gate, Gemini path, `GET /channel/analyze`, tests | `supabase/migrations/20260427100000_b31_channel_formulas.sql`; `cloud-run/getviews_pipeline/channel_analyze.py`; `cloud-run/main.py` `@app.get("/channel/analyze")`; `cloud-run/tests/test_channel_analyze.py` |
| **B.3.2** | Posting cadence + KPI aggregation, 7d cache behaviour | Implemented in `channel_analyze.py` (`compute_live_signals`, `_build_kpis`, cache read / `force_refresh`) |
| **B.3.3** | `/app/channel` route, `FormulaBar`, thin corpus UI, data wiring | `src/routes.ts` → `routes/_app/channel/route.tsx` + `ChannelScreen.tsx`; `useChannelAnalyze.ts`; `FormulaBar.tsx`; thin copy per plan |
| **B.3.4** | Retire chat `competitor_profile` / `own_channel` streams; Soi Kênh → channel; KOL CTA | `ChatScreen.tsx` handoff; `EmptyStates.tsx` modal; `QuickActions.tsx`; `KolScreen.tsx` + `KolStickyDetailCard.tsx`; `src/lib/channelHandle.ts` |
| **B.3.5** | Design audit artifact + token sweep + ship must-fix | `phase-b-design-audit-channel.md`; this file; **pixel pass** below (KpiGrid `channel` variant, rhythm, breakpoint, tiles, formula line-height) |

---

## 2. Token & banned-pattern sweep (B.3 web surface)

**Paths:** `src/routes/_app/channel/**/*.tsx`, `src/components/v2/FormulaBar.tsx`, `src/components/v2/KpiGrid.tsx` (channel variant only uses `gv-*`).

| Check | Result |
|--------|--------|
| Raw `#hex` in JSX | **0** (excluding API `bg_color` on thumbnails) |
| `--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*` | **0** |
| `rgba(` / `rgb(` in these files | **0** |

---

## 3. Pixel parity vs `channel.jsx` + §B.3 spec

| Element | Reference / plan | Previous gap | Resolution |
|---------|------------------|--------------|--------------|
| Hero KPI strip | Label **9px** uc mb **4px**; value **22px** lh **1.1**; delta **10px** mt **4px** pos-deep; cell **canvas**; fixed **2×2** | `KpiGrid` reused video strip (**30px** values, **paper** cells, auto-fit cols) | **`KpiGrid variant="channel"`** — canvas cells, 22px/1.1, mb-1 / mt-1, `grid-cols-2` only |
| Formula segment detail | **lineHeight 1.3** | `leading-snug` (~1.375) | **`leading-[1.3]`** in `FormulaBar` |
| Bio | **lineHeight 1.4** | `leading-snug` | **`leading-[1.4]`** |
| Formula block → two-col | **marginBottom 36** on formula wrapper | Uniform `gap-7` (28px) only | **Split stack**: form+hero+formula in `gap-7` group; **`mt-9` (36px)** on `ch-grid` |
| Responsive | **`max-width: 900px`** → 1 col | `min-[900px]:` → at **900px** ref is still 1 col | **`min-[901px]:grid-cols-2`** + default `grid-cols-1` on hero + bottom grid |
| Video thumb | **radius 6**, no border, overlay text only | Extra **rule border** + **Play** icon | **Removed** border + icon; overlay matches mono 10 + position |
| Lesson title | **marginBottom 2** under title | Only body `mt-0.5` | **`mb-0.5`** on title row |

**Already aligned earlier:** shell `1280` + `24×28×80`; back **18px**; hero **px-8 py-7**; chips **mt 18px** + `posting · time`; formula bar **80px / 8px radius / ink border**; thin empty copy + **ink-4**; section titles; chip **gap 8** (`gap-2`).

**Intentional product deltas (not defects):** `TopBar` + pulse + KOL shortcut; “Kênh khác” form; script CTA disabled until `/script`; `computed_at` footer.

**Deferred by plan:** `PostingHeatmap`.

---

## 4. Verdict

- **B.3.1–B.3.4:** Implemented with traceable files and tests.  
- **B.3.5 / pixel-perfect:** Prior gaps (KPI typography, cell surface, vertical rhythm **36px**, breakpoint **901px**, video tile chrome, formula/bio line-height, lesson title spacing) are **closed in code** accompanying this audit.  
- **B.3 closure:** **Green** — remaining items are product extensions or deferred scope, not blocking spec violations.

**Related artifacts:** [`phase-b-design-audit-channel.md`](phase-b-design-audit-channel.md), [`phase-b-b33-channel-audit.md`](phase-b-b33-channel-audit.md).
