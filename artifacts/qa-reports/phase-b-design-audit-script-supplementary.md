# Phase B · B.4 — supplementary design parity (`/app/script`)

**Date:** 2026-04-19 (reconciled 2026-04-19)
**Parent audits:** `phase-b-design-audit-script.md` (B.4.6), `phase-b-b4-implementation-audit.md` (post-push checklist).
**Scope:** Second-pass drift check against `artifacts/uiux-reference/screens/script.jsx` after B.4.1–B.4.6 closed on `main`, plus follow-up polish through **`e36a2db`** (TopBar / citation / forecast type), **`738f3b2`** (S-3 + M-2), **`8731a61`** (script UIUX alignment).

---

## Token & banned-pattern sweep (re-verified)

`grep -nE '#[0-9a-fA-F]{3,8}\b|--ink-soft|--purple|--border-active|--gv-purple|text-white|bg-black|rgba\(|rgb\('`

| Scope | Hits |
|---|---|
| `src/routes/_app/script/**/*.tsx` | **0** (benchmark blues use `var(--gv-chart-benchmark)` or documented literals in meter/forecast where ref uses `rgb`) |
| `src/components/v2/{Script*, Scene*, Mini*, HookTiming*, DurationInsight, CardInput, CitationTag}*.tsx` | **0** |

`var(--gv-chart-benchmark)` is defined in `src/app.css` as `rgb(0, 159, 250)` — the token-catalog equivalent of the reference's raw `rgb(0,159,250)` literal. Consistent with the B.3 backend-palette precedent.

---

## Closed since initial supplementary audit (`8f49d65` → `e36a2db`)

| ID | Resolution | Notes |
|----|--------------|-------|
| **M-2** | **Done** (`738f3b2`) | Hook row delta: literal `▲{h.delta}` + `text-[color:var(--gv-chart-benchmark)]`. |
| **S-1** | **Done** (`8731a61`, reinforced `e36a2db`) | Outer shells: `CardInput`, `ScriptPacingRibbon`, `SceneIntelligencePanel` cards use **`rounded-none`**; `CitationTag` **`rounded-none`**. Inner chips / clips keep intentional radius. |
| **S-2** | **Done** (`8731a61`) | Tip card: `leading-[1.25]` `tracking-[-0.01em]` on serif tip (`SceneIntelligencePanel`). |
| **S-3** | **Done** (`738f3b2`) | `overlayCorpusCount` from `activeIntel?.sample_size` → **“Trong N video thắng…”** when `N > 0`; generic fallback otherwise (hook `citation.sample_size` **not** used). |
| **TopBar / studio chrome** | **Done** (`e36a2db`) | `CREATOR` / **Xưởng Viết** `TopBar` restored with pulse strip, **Đã Lưu** (disabled), **Phân tích mới** → `/app/chat`, matching Video/Home pattern. |
| **Padding stack** | **Done** (`e36a2db`) | Script content wrapper relies on **`.gv-route-main`** padding only (`mx-auto w-full max-w-[1380px]`). |
| **Card labels + forecast kicker** | **Done** (`e36a2db`) | `CardInput` labels: **`gv-uc`**; `ScriptForecastBar` kicker **`gv-uc`**; view count **`gv-tight`** + **`leading-none`** + **`tracking-[-0.02em]`**. |

---

## Remaining drifts vs `script.jsx`

### must-fix

| ID | Item | Reference | Shipped | Fix |
|----|------|-----------|---------|-----|
| M-1 | **Content max-width capped at 1280px** — `<main className="gv-route-main gv-route-main--1280">` forces `max-width: 1280px` (`src/app.css:519-521`). Inner `max-w-[1380px]` never exceeds parent. | `maxWidth: 1380` (`script.jsx:31`) | Still **`gv-route-main--1280`** on `ScriptScreen.tsx`. | Drop **`gv-route-main--1280`** (use bare **`gv-route-main`** = 1320px) **or** add **`.gv-route-main--1380`** in `app.css` and use it on script only. |

### should-fix

*None open* — S-1/S-2/S-3 from the initial supplementary pass are closed above.

### consider

| ID | Item | Note |
|----|------|------|
| C-1 | **Camera-swatch palette: pastel avatars vs navy/plum reference.** `ScriptShotRow.tsx` cycles `--gv-avatar-*`; reference uses moody hexes. | Optional token catalog `--gv-shot-cam-*` if design wants cinematic swatches. |
| C-2 | **TopBar + route padding.** TopBar is **restored** on script (`e36a2db`). Inner duplicate `pt/px` removed; breathing room comes from `.gv-route-main`. | No action unless TopBar is removed again. |
| C-3 | **`script_no` frozen at `14` via `useState`.** | Wire to real counter or `const` when product needs it. |
| C-4 | **Disabled header actions use `title="Sắp có"`.** | Revisit when Copy/PDF/recording ship. |

---

## Backend parity check (not in primary audit)

Unchanged from prior revision — see parent `phase-b-b4-implementation-audit.md` and `test_script_generate.py` / `test_scene_intelligence.py` coverage.

---

## Test coverage

Unchanged from prior revision — gap remains: no `ScriptScreen.test.tsx` / primitive render tests (recommended follow-up).

---

## Deferred / aligned-with-plan

Unchanged — `script_save`, Copy/PDF/Chế độ quay, LLM generation, `script_save` analytics.

---

## Verdict

**Green with one must-fix** — supplementary **M-2** and **S-1 / S-2 / S-3** are closed on `main`. **M-1** (1280 vs 1380 route max-width) is the only remaining **must-fix** from this pass. **Consider** items are optional palette / copy polish.

Next: one small commit for **M-1** (width utility or drop `--1280`) when product confirms target width (1320 vs 1380).

---

## Traceability

| Milestone | Commit |
|-----------|--------|
| B.4.1–B.4.3 foundation | `b25bba9` |
| B.4.4–B.4.5 prefill | `57f22ea` |
| B.4.6 design audit + tokens | `57f22ea` |
| `POST /script/generate` + analytics | `e3cf69b` |
| PWA / Rolldown build fix | `064e345` |
| Script UIUX ref (sharp cards, typography, no duplicate back row) | `8731a61` |
| Channel CTA script icon 13px | `99eca06` |
| S-3 + M-2 (overlay count + ▲ delta) | `738f3b2` |
| TopBar restore, flat citation, forecast type | `e36a2db` |
| This supplementary audit (initial) | `8f49d65` |
