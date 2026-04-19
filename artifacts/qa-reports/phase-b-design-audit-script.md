# Phase B · B.4.6 — design audit (`/app/script` vs `script.jsx`)

**Date:** 2026-04-19  
**Reference:** `artifacts/uiux-reference/screens/script.jsx`  
**Shipped surface:** `src/routes/_app/script/ScriptScreen.tsx` + v2 primitives listed below.

---

## Executive summary

Section-by-section parity with the UIUX reference is **strong** on layout (3-col → 2-col → 1-col breakpoints **1240px / 880px**), component inventory (pacing ribbon, shot rows, hook meter, duration insight, forecast bar, scene stack, citation), and **design tokens**: no raw `#hex` in script-route JSX, no banned purple-era CSS variables (`--ink-soft`, `--purple`, `--border-active`, `--gv-purple-*`) in the audited files.

**Must-fix (token literals):** Tailwind `text-white`, `text-white/85`, and `bg-black/55` in script primitives were **not** expressed as `var(--gv-*)` paths. These are **closed in code** in the same change set as this report (`ScriptShotRow.tsx`, `SceneIntelligencePanel.tsx`). Re-verified with grep (see sweep).

**Should-fix:** A few copy/spacing deltas vs the static reference remain intentional (shell `TopBar`, dynamic citation, API-backed hooks). **Closed:** `DurationInsight` “vùng vàng” tone and shot-row “✓” pacing chip now use `--gv-chart-benchmark` to match the reference’s benchmark blue thread.

**Consider:** Hiding the entire right rail when `sample_size < 30` (plan **Risks** table) — we instead show a **non-blocking banner** when the active scene row reports `0 < sample_size < 30`, keeping placeholders for empty reference clips.

---

## Token & banned-pattern sweep (authoritative)

Command (approximate):

```bash
rg -n '#[0-9a-fA-F]{3,8}\\b|--ink-soft|--purple|--border-active|--gv-purple|text-white|bg-black' \
  src/routes/_app/script \
  src/components/v2/ScriptPacingRibbon.tsx \
  src/components/v2/ScriptShotRow.tsx \
  src/components/v2/HookTimingMeter.tsx \
  src/components/v2/DurationInsight.tsx \
  src/components/v2/SceneIntelligencePanel.tsx \
  src/components/v2/ScriptForecastBar.tsx \
  src/components/v2/CardInput.tsx \
  src/components/v2/CitationTag.tsx \
  src/components/v2/MiniBarCompare.tsx
```

| Area | Result (post-fix) |
|------|-------------------|
| Raw `#RRGGBB` in JSX classNames / inline styles above | **0** |
| Banned legacy tokens | **0** |
| `text-white` / `bg-black/…` in audited primitives | **0** (replaced with `--gv-canvas` / `color-mix` on `--gv-ink` / `--gv-canvas`) |

**Note:** `src/app.css` defines palette literals (e.g. `--gv-chart-benchmark: rgb(0, 159, 250);`) — that is the **token catalog**, not screen-local hex. Consistent with B.3 supplementary audit for channel tile colors.

---

## Section-by-section vs `script.jsx`

### Shell / route framing

| Topic | Reference | Shipped | Verdict |
|-------|-----------|---------|---------|
| Top chrome | None (bare `ScriptScreen`) | `AppLayout` + `TopBar` (`CREATOR` / **Xưởng Viết**) + **Về Studio** | **Consider** — matches other GV routes (`/video`, `/channel`); not a regression. |
| Max width / padding | `maxWidth: 1380`, `padding: 24px 28px 80px` | `max-w-[1380px]`, `px-4` → `min-[376px]:px-7`, `pb-20 pt-2` | **Consider** — vertical rhythm differs slightly due to `TopBar` + back row. |

### Header (kicker + H1 + actions)

| Topic | Reference | Shipped | Verdict |
|-------|-----------|---------|---------|
| Kicker | `XƯỞNG VIẾT · KỊCH BẢN SỐ 14` | Same + `scriptNo` state (14) | **OK** |
| Title typography | `clamp(26px, 3vw, 36px)` serif | `clamp(1.625rem, 3vw, 2.25rem)` | **OK** (equivalent) |
| Border | `borderBottom: 2px solid var(--ink)` | `border-b-2 border-[color:var(--gv-ink)]` | **OK** |
| Actions | Ghost Copy/PDF + primary **Chế độ quay** | Same trio, **disabled** (`title="Sắp có"`) | **OK** — plan defers persistence / modes. |

### Left column — inputs

| Block | Reference | Shipped | Verdict |
|-------|-----------|---------|---------|
| `CardInput` shell | `padding: 14`, `1px solid var(--rule)`, paper | `p-3.5` (=14px), `gv-rule` / `gv-paper` | **OK** |
| Label row | mono uc, `9.5px`, `letterSpacing 0.16em`, `ink-4`, `marginBottom: 10` | `mb-2.5` (=10px), matching tracking | **OK** |
| Hook list | First 4 hooks, selected = ink bg | API `hook_patterns` slice(4), same interaction | **OK** — data-backed upgrade. |
| Hook meter + caption | Meter + 0.8–1.4s + 38% copy | `HookTimingMeter` + same copy (generic “trong ngách” vs ref “Tech”) | **Should-fix (parked)** — niche label in sentence optional follow-up. |
| Duration + insight | Range + `DurationInsight` | Same | **OK** |
| Tone row | chip / chip-accent | `Chip` component `accent` / `default` | **OK** |
| CTA | Accent **Tạo lại với AI** | Disabled + tooltip for POST `/script/generate` | **OK** |
| Citation | Static `CitationTag n={47}` | `hookData.citation` when `sample_size > 0` | **OK** — product-correct. |

### Middle column — pacing + shots + forecast

| Block | Reference | Shipped | Verdict |
|-------|-----------|---------|---------|
| Pacing ribbon container | `1px solid ink`, paper, `padding: 14`, bar height **38** | `ScriptPacingRibbon` matches | **OK** |
| Dual bars | yours `20%`/`25%`, niche `55%`/`25%`, niche bar **opacity 0.5** | Same geometry + opacity | **OK** |
| Timeline row | Height **16** | `h-4` (16px) | **OK** |
| Shot row grid | `90px 100px 1fr 1fr` | Same | **OK** |
| Active shadow | `3px 3px 0 var(--ink)` | `shadow-[3px_3px_0_var(--gv-ink)]` | **OK** |
| Camera well | Rotating hex fills in ref | Rotating `--gv-avatar-*` | **OK** — token-native analogue. |
| Forecast bar | Ink bar, `padding: 16px 20px`, serif **28px** forecast, benchmark % + accent hook score, CTA | `ScriptForecastBar` matches; CTA disabled | **OK** |

### Right column — scene intelligence

| Block | Reference | Shipped | Verdict |
|-------|-----------|---------|---------|
| Tip card | Ink bg, mono kicker, serif tip | `SceneIntelligencePanel` card 1 | **OK** |
| Shot length + mini bars | `MiniBarCompare` + corpus/winner line | `MiniBarCompare` + same line | **OK** |
| Overlay library | Up to 3 chips, `7px 10px`, 11px, plus icon | Slightly tighter Tailwind (`py-1.5`) | **Consider** — sub-pixel parity optional. |
| Reference clips | `80px`, `9/13`, thumb + duration badge | `w-20` (80px), `aspect-[9/13]`, links to `/app/video` | **OK** — shipped supersedes static buttons. |
| Thin corpus | (not in ref) | Banner when `0 < sample_size < 30` | **OK** — mitigates plan risk without removing rail. |

### Responsive grid

| Breakpoint | Reference CSS | Shipped Tailwind | Verdict |
|------------|---------------|------------------|---------|
| `≤1240px` | 2 cols; right rail spans full width, **row** + horizontal scroll | `min-[881px]:max-[1240px]:grid-cols-[280px_1fr]` + `col-span-2` + `flex-row` + `overflow-x-auto` + `min-w-[280px]` children | **OK** |
| `≤880px` | 1 col; right rail **column** | `max-[880px]:grid-cols-1` + `max-[880px]` stack | **OK** |

---

## Tiered findings

### must-fix

| ID | Item | Resolution |
|----|------|------------|
| M-1 | Non–`gv-*` colour utilities (`text-white`, `text-white/85`, `bg-black/55`) in script primitives | **Done:** `ScriptShotRow`, `SceneIntelligencePanel` now use `var(--gv-canvas)` / `color-mix(in_srgb, var(--gv-ink)_58%, transparent)` etc. |

### should-fix

| ID | Item | Resolution |
|----|------|------------|
| S-1 | `DurationInsight` “★ vùng vàng” used `--gv-pos-deep` while reference uses benchmark blue | **Done:** `text-[color:var(--gv-chart-benchmark)]`. |
| S-2 | Shot-row “✓” pacing chip text colour vs reference rgb benchmark | **Done:** `text-[color:var(--gv-chart-benchmark)]` paired with existing benchmark mix background. |
| S-3 | Hook helper copy says “trong ngách” vs ref “trong ngách Tech” | **Parked** — needs niche label prop if we want 1:1. |

### consider

| ID | Item | Note |
|----|------|------|
| C-1 | Shell `TopBar` + back control | Keeps parity with `/video` / `/channel`; reference is screen-only. |
| C-2 | Full **hide** of right rail when `sample_size < 30` | Plan risk suggested hiding; shipped **banner** preserves layout + educates. Upgrade path: collapse to single “thin” card. |
| C-3 | Overlay chip `padding: 7px 10px` exact | Tailwind `px-2.5 py-1.5` — close enough. |

---

## B.4 closure criteria (plan §B.4.6)

| Criterion | Status |
|-----------|--------|
| Audit file at `artifacts/qa-reports/phase-b-design-audit-script.md` | **Yes** |
| Section-by-section vs `script.jsx` | **Above** |
| Token grep (hex + banned list) on new screen files | **Green** (after M-1) |
| Must-fix items shipped | **Yes** (M-1 + should-fix S-1/S-2 bundled) |

---

## Suggested follow-ups (not blocking B.4)

1. Pass niche display name into hook-delay helper copy (S-3).
2. `logUsage` events for `script_save` / `channel_to_script` per plan measurement table (if not already wired elsewhere).
3. Vitest snapshot or RTL smoke for `ScriptPacingRibbon` geometry (optional).
